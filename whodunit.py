# WhoDunIt
#
# Determines the owner(s) of lines in a file. Can operate on a single file
# or directory tree (with results file-by-file). Goal is to use this info
# as a hint on who to contact regarding the file. It collects the counts
# of lines for a commiter, per commit.
#
# Usage:
#    whodunit.py [-h] [-d] [-v] [-m] [-s {date,size}] file-or-directory
# Where:
# -h, --help            show this help message and exit.
# -d, --details         Show individual commit/user details.
# -v, --verbose         Show additional info on each commit.
# -m, --max             Maximum number of users/commits to show. Default=5,
#                       use 0 for all.
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
# commiter's name, and commiter's email are also shown.
#
# In the case of sorting by cover, you must specify a directory (at the root
# of the project tree) with coverage HTML files to process. The output will
# show the owners of the lines in modules in the report that are flagged
# as missing coverage or partial coverage. The line number, committer, and
# date will be shown.

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

    def show(self, verbose):
        author = self.author
        author_width = 25
        committer = ''
        commit_date = self.date_to_str(self.committer_time, self.committer_tz,
                                       verbose)
        if verbose:
            author += " %s" % self.author_mail
            author_width = 50
            committer = " %s %s" % (self.committer, self.committer_mail)
        return "    {} {:5d} {:{}s} {}{}".format(
            self.uuid[:8], self.line_count, author, author_width,
            commit_date, committer)

    def __str__(self):
        return "{0} {1:5d} {2} {3} {4}".format(self.uuid[:8], self.line_count,
                                               self.author, self.author_mail,
                                               self.date)

    def __repr__(self):
        return "%s(%s) %s %s %d" % (self.__class__, self.uuid, self.author,
                                    self.author_mail, self.line_count)


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


def find_modules(top):
    """Look for git files in tree. Will handle all lines."""
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist, "*"):
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


def parse_info_records(lines):
    commits = {}
    in_new_record = False
    for line in lines.splitlines():
        m = uuid_line_re.match(line)
        if m:
            uuid = m.group(1)
            line_number = int(m.group(2))
            if uuid not in commits:
                record = BlameRecord(uuid, line_number)
                in_new_record = True
            else:
                commits[uuid].line_count += 1
            continue
        if in_new_record:
            if code_line_re.match(line):
                record.validate()
                commits[uuid] = record
                in_new_record = False
                continue
            m = attr_line_re.match(line)
            if m:
                record.store_attribute(m.group(1), m.group(2))
    return commits


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
    # First sort commits by author email
    sorted_commits = sorted(commits.values())
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
    return sorted(commits.values(),
                  key=lambda x: x.committer_time, reverse=True)


def main(args):

    if args.sort_by == 'cover':
        if not os.path.isdir(args.root):
            parser.error("Must specify a directory, when sorting by coverage")
        matches = find_partial_coverage_modules(args.root)
    elif os.path.isdir(args.root):
        matches = find_modules(args.root)
    elif os.path.isfile(args.root):
        matches = iter(([args.root], []))
    else:
        parser.error("Must specify a file or a directory to process")
    blame_infos = collect_blame_info(matches)
    for info in blame_infos:
        commits = parse_info_records(info)
        if args.sort_by == 'size':
            sorted_commits = sort_by_size(commits)
        else:
            sorted_commits = sort_by_date(commits)
        limit = None if args.max == 0 else args.max
        top_n = [c.author for c in sorted_commits[:limit]]
        print("(%s)" % ','.join(top_n))
        if args.details:
            for commit in sorted_commits[:limit]:
                print(commit.show(args.verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Determine ownership for file or tree of files.')
    parser.add_argument('-d', '--details', action='store_true',
                        help='Show details in addition to summary.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        dest='verbose',
                        help='Show additional info on each commit.')
    parser.add_argument('-m', '--max', action='store', type=int, default=5,
                        help='Maximum number of users/commits to show. '
                        'Default=5, use 0 for all.')
    parser.add_argument('-s', '--sort', dest='sort_by', action='store',
                        choices={'date', 'size', 'cover'}, default='date',
                        help="Sort order for report. Default='date'.")
    parser.add_argument(dest='root', metavar='file-or-dir')
    main(parser.parse_args())
