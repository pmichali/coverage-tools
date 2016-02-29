#!/usr/bin/env python
# WhoDunIt
#
# Determines the owner(s) of lines in a file. Can operate on a single file
# or directory tree (with results file-by-file). Goal is to use this info
# as a hint on who to contact regarding the file. It collects the counts
# of lines for a commiter, per commit.
#
# Usage:
#    whodunit.py [-h] [-d] [-v] [-m] [-f] [-s {date,size,cover}] file-or-dir
# Where:
# -h, --help            show this help message and exit.
# -d, --details         Show individual commit/user details.
# -v, --verbose         Show additional info on each commit.
# -m, --max             Maximum number of users/commits to show. Default=0
#                       (show all).
# -f, --filter          Filter regex for filename. Default='*'
# -s {date,size,cover}, --sort {date,size,cover} Sort order for report.
#                       Default='date'.
#
# Output will have file path and name, and then committers, in priority order
# as selected by the options (date/size).
#
# If the --details option is chosen, subsequent lines will show details for
# each committer. In the case of sorting by size, the committer with the
# most lines in all commits, will be shown first, along with the total line
# count.
#
# In the case of sorting by date, the committer with the commit having the
# most recent date will be shown first, along with the number of lines for
# that commit.
#
# If the --verbose option is selected, then the author's email address,
# commiter's name, and commiter's email are also shown. The time and time-
# zone will be shown for the commit date.
#
# In the case of sorting by cover, you must specify a directory (at the root
# of the project tree) with coverage HTML files to process. You cannot specify
# the --max' option, and detailed output is assumed.
#
# The output will show the lines from  modules in the report that are flagged
# as missing coverage or partial coverage. The commit ID, line number,
# committer, and date will be shown. With the --verbose flag, the committer's
# email and detailed date/time will be shown.

from __future__ import print_function

import argparse
import datetime
import fnmatch
import itertools
import operator
import os
import re
import subprocess


uuid_line_re = re.compile(r'([a-f0-9]{40})\s+\d+\s+(\d+)')
code_line_re = re.compile(r'\s')
attr_line_re = re.compile(r'(\S+)\s(.+)')

title_re = re.compile(r'\s*<title>Coverage for ([^:]+):\s+(\d+)%<\/title>')
source_re = re.compile(r'<p id="n(\d+)" class="stm (mis|par)')
end_re = re.compile(r'\s*<td class="text">')


class BadRecordException(Exception):
    pass


class SourceNotFound(Exception):
    pass


class BlameRecord(object):

    def __init__(self, uuid, line_number):
        self.uuid = uuid
        self.line_number = line_number
        self.line_count = 1

    def store_attribute(self, key, value):
        """Store blame info we are interested in."""
        if key == 'summary' or key == 'filename' or key == 'previous':
            return
        attr = key.replace('-', '_')
        if key.endswith('-time'):
            value = int(value)
        setattr(self, attr, value)

    @staticmethod
    def date_to_str(time_stamp, time_zone, verbose=True):
        date_time = datetime.datetime.utcfromtimestamp(time_stamp)
        offset_hrs = int(time_zone)/100
        offset_mins = int(time_zone[-2])
        date_time += datetime.timedelta(hours=offset_hrs,
                                        minutes=offset_mins)
        if verbose:
            return date_time.strftime('%Y-%m-%d %H:%M:%S ') + time_zone
        else:
            return date_time.strftime('%Y-%m-%d')

    @property
    def date(self):
        return self.date_to_str(self.committer_time, self.committer_tz)

    def __cmp__(self, other):
        """Compare records by author's email address.

        It's possible for commits by the same author to have different name
        spelling. Will use the email address, which hopefully will not change
        as often. Also using author, rather than committer, as there could be
        commits where the last patchset was by someone else.
        """
        return cmp(self.author_mail, other.author_mail)

    def validate(self):
        if not hasattr(self, 'author_time') or not hasattr(self, 'author_tz'):
            raise BadRecordException("Missing author time information")
        if (not hasattr(self, 'committer_time') or
                not hasattr(self, 'committer_tz')):
            raise BadRecordException("Missing committer time information")
        if not hasattr(self, 'author'):
            raise BadRecordException("Missing author name")
        if not hasattr(self, 'author_mail'):
            raise BadRecordException("Missing author email")
        if not hasattr(self, 'committer'):
            raise BadRecordException("Missing committer name")
        if not hasattr(self, 'committer_mail'):
            raise BadRecordException("Missing committer email")

    def show(self, options):
        """Display one commit line.

        Output varies based on type of reporting done. For 'size' and 'date'
        reporting, the output will be:
            <uuid> <#lines> <author> <short-commit-date>

        If verbose flag set, the output will be:
            <uuid> <#lines> <author+email> <long-date> <committer+email>

        If report type is 'cover', the number of lines will be the line
        number in the source file, instead of line count.
        """
        verbose = options.verbose
        coverage_mode = options.sort_by == 'cover'
        author = self.author
        author_width = 25
        committer = ''
        commit_date = self.date_to_str(self.committer_time, self.committer_tz,
                                       verbose)
        if coverage_mode:
            line_info = self.lines
            line_width = 11
        else:
            line_info = str(self.line_count)
            line_width = 5
        if verbose:
            author += " %s" % self.author_mail
            author_width = 50
            committer = " %s %s" % (self.committer, self.committer_mail)
        return "    {} {:>{}s} {:{}s} {}{}".format(
            self.uuid[:8], line_info, line_width, author, author_width,
            commit_date, committer)

    def __str__(self):
        return "{0} {1:5d} {2} {3} {4}".format(self.uuid[:8], self.line_count,
                                               self.author, self.author_mail,
                                               self.date)

    def __repr__(self):
        return "%s(%s) %s %s %d %d" % (self.__class__, self.uuid, self.author,
                                       self.author_mail, self.line_count,
                                       self.line_number)


def make_ranges(lines):
    """Convert list of lines into list of line range tuples.

    Only will be called if there is one or more entries in the list. Single
    lines, will be coverted into tuple with same line.
    """
    start_line = last_line = lines.pop(0)
    ranges = []
    for line in lines:
        if line == (last_line + 1):
            last_line = line
        else:
            ranges.append((start_line, last_line))
            start_line = line
            last_line = line
    ranges.append((start_line, last_line))
    return ranges


def determine_coverage(coverage_file):
    """Scan the summary section of report looking for coverage data.

    Will see CSS class with "stm mis" (missing coverage), or "stm par"
    (partial coverage), and can extract line number. Will get file name
    from title tag.
    """
    lines = []
    source_file = 'ERROR'
    for line in coverage_file:
        m = title_re.match(line)
        if m:
            if m.group(2) == '100':
                return ('', [])
            source_file = m.group(1)
            continue
        m = source_re.match(line)
        if m:
            lines.append(int(m.group(1)))
            continue
        if end_re.match(line):
            break
    line_ranges = make_ranges(lines)
    return (source_file, line_ranges)


def find_partial_coverage_modules(top):
    """Look at coverage report files for lines of interest.

    Will verify that the source file is within the project tree, relative
    to the coverage directory.
    """
    root = os.path.abspath(top)
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist, "*.html"):
            if name == 'index.html':
                continue
            with open(os.path.join(path, name)) as cover_file:
                source_file, line_ranges = determine_coverage(cover_file)
            if not source_file:
                continue
            source_file = os.path.abspath(
                os.path.join(root, '..', source_file))
            if os.path.isfile(source_file):
                yield (source_file, line_ranges)
            else:
                raise SourceNotFound("Source file %(file)s not found "
                                     "at %(area)s" %
                                     {'file': os.path.basename(source_file),
                                      'area': os.path.dirname(source_file)})


def is_git_file(path, name):
    """Determine if file is known by git."""
    os.chdir(path)
    p = subprocess.Popen(['git', 'ls-files', '--error-unmatch', name],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    return p.returncode == 0


def find_modules(top, filter):
    """Look for git files in tree. Will handle all lines."""
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist, filter):
            if is_git_file(path, name):
                yield (os.path.join(path, name), [])


def build_line_range_filter(ranges):
    return ['-L %d,%d' % r for r in ranges]


def collect_blame_info(matches):
    old_area = None
    for filename, ranges in matches:
        area, name = os.path.split(filename)
        if area != old_area:
            print("\n\n%s/\n" % area)
            old_area = area
        print("%s " % name, end="")
        filter = build_line_range_filter(ranges)
        command = ['git', 'blame', '--line-porcelain'] + filter + [name]
        os.chdir(area)
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if err:
            print(" <<<<<<<<<< Unable to collect 'git blame' info:", err)
        else:
            yield out


def parse_info_records(lines, unique_commits=False):
    records = []
    commits = set()
    in_new_record = False
    for line in lines.splitlines():
        m = uuid_line_re.match(line)
        if m:
            uuid = m.group(1)
            line_number = int(m.group(2))
            if unique_commits or uuid not in commits:
                record = BlameRecord(uuid, line_number)
                commits.add(uuid)
                in_new_record = True
            else:
                record.line_count += 1
            continue
        if in_new_record:
            if code_line_re.match(line):
                record.validate()
                records.append(record)
                in_new_record = False
                continue
            m = attr_line_re.match(line)
            if m:
                record.store_attribute(m.group(1), m.group(2))
    return records


def merge_user_commits(commits):
    """Merge all the commits for the user.

    Aggregate line counts, and use the most recent commit (by date/time)
    as the representative commit for the user.
    """
    user = None
    for commit in commits:
        if not user:
            user = commit
        else:
            if commit.committer_time > user.committer_time:
                commit.line_count += user.line_count
                user = commit
            else:
                user.line_count += commit.line_count
    return user


def sort_by_size(commits):
    """Sort by commit size, per author."""
    # First sort commits by author email
    sorted_commits = sorted(commits)
    users = []
    # Group commits by author email, so they can be merged
    for _, group in itertools.groupby(sorted_commits,
                                      operator.attrgetter('author_mail')):
        if group:
            users.append(merge_user_commits(group))
    # Finally sort by the (aggregated) commits' line counts
    return sorted(users, key=operator.attrgetter('line_count'), reverse=True)


def sort_by_date(commits):
    """Sort commits by the committer date/time."""
    return sorted(commits, key=lambda x: x.committer_time, reverse=True)


def line_range(first_line, last_line):
    if first_line != last_line:
        return "%d-%d" % (first_line, last_line)
    else:
        return str(first_line)


def sort_by_contiguous_commit(commits):
    """Consolidate adjacent lines, if same commit ID.

    Will modify line number to be a range, when two or more lines with the
    same commit ID.
    """
    sorted_commits = []
    if not commits:
        return sorted_commits
    prev_commit = commits.pop(0)
    prev_line = prev_commit.line_number
    prev_uuid = prev_commit.uuid
    for commit in commits:
        if (commit.uuid != prev_uuid or
                commit.line_number != (prev_line + 1)):
            prev_commit.lines = line_range(prev_commit.line_number, prev_line)
            sorted_commits.append(prev_commit)
            prev_commit = commit
        prev_line = commit.line_number
        prev_uuid = commit.uuid
    # Take care of last commit
    prev_commit.lines = line_range(prev_commit.line_number, prev_line)
    sorted_commits.append(prev_commit)
    return sorted_commits


def sort_by_name(names):
    """Sort by last name, uniquely."""

    def last_name_key(full_name):
        parts = full_name.split(' ')
        if len(parts) == 1:
            return full_name.upper()
        last_first = parts[-1] + ' ' + ' '.join(parts[:-1])
        return last_first.upper()

    return sorted(set(names), key=last_name_key)


def unique_authors(names):
    """Unique list of authors, but preserving order."""
    seen = set()
    seen_add = seen.add  # Assign to variable, so not resolved each time
    return [x.author for x in names
            if not (x.author in seen or seen_add(x.author))]


def main(args):
    coverage_mode = args.sort_by == 'cover'
    args.root = os.path.abspath(args.root)
    if coverage_mode:
        if not os.path.isdir(args.root):
            parser.error("Must specify a directory, when sorting by coverage")
        if args.max != 0:
            parser.error("Cannot specify a limit to number of users/commits "
                         "to show, when sorting coverage reports")
        args.details = True  # Force on
        matches = find_partial_coverage_modules(args.root)
    elif os.path.isdir(args.root):
        matches = find_modules(args.root, args.filter)
    elif os.path.isfile(args.root):
        matches = iter(([args.root], []))
    else:
        parser.error("Must specify a file or a directory to process")
    blame_infos = collect_blame_info(matches)
    all_authors = []
    for info in blame_infos:
        commits = parse_info_records(info, coverage_mode)
        if args.sort_by == 'size':
            sorted_commits = sort_by_size(commits)
        elif args.sort_by == 'date':
            sorted_commits = sort_by_date(commits)
        else:
            sorted_commits = sort_by_contiguous_commit(commits)
        limit = None if args.max == 0 else args.max
        top_n = unique_authors(sorted_commits[:limit])
        all_authors += top_n
        # Don't alter, as names in sort (date/size) order
        print("(%s)" % ', '.join(top_n))
        if args.details:
            for commit in sorted_commits[:limit]:
                print(commit.show(args))
    print("\n\nAll authors: %s" % ', '.join(sort_by_name(all_authors)))

def setup_parser():
    parser = argparse.ArgumentParser(
        description='Determine ownership for file or tree of files.')
    parser.add_argument('-d', '--details', action='store_true',
                        help='Show details in addition to summary.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        dest='verbose',
                        help='Show additional info on each commit.')
    parser.add_argument('-m', '--max', action='store', type=int, default=0,
                        help='Maximum number of users/commits to show. '
                        'Default=0 (show all).')
    parser.add_argument('-s', '--sort', dest='sort_by', action='store',
                        choices={'date', 'size', 'cover'}, default='date',
                        help="Sort order for report. Default='date'.")
    parser.add_argument('-f', '--filter', action='store', default="*",
                        help="Filter regular expression for file name. "
                             "Default='*', which includes hidden files")
    parser.add_argument(dest='root', metavar='file-or-dir')
    return parser

if __name__ == "__main__":
    parser = setup_parser()
    main(parser.parse_args())
