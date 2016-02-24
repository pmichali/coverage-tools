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
# -s {date,size}, --sort {date,size} Sort order for report. Default=date.
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

import argparse
import datetime
import fnmatch
import itertools
import operator
import os
import re
import subprocess


uuid_line_re = re.compile(r'([a-f0-9]{40})\s')
code_line_re = re.compile(r'\s')
attr_line_re = re.compile(r'(\S+)\s(.+)')


class BadRecordException(Exception):
    pass


class BlameRecord(object):

    def __init__(self, uuid):
        self.uuid = uuid
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


def find_modules(top):
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist, "*.py"):
            yield os.path.join(path, name)


def find_coverage_modules(top):
    # Check filename part is 'cover'?
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist, "*.html"):
            yield os.path.join(path, name)


def collect_blame_info(filenames):
    old_area = None
    for filename in filenames:
        area, name = os.path.split(filename)
        if area != old_area:
            print "\n\n%s/\n" % area
            old_area = area
        print name,
        os.chdir(area)
        p = subprocess.Popen(['git', 'blame', '--line-porcelain', name],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if err:
            print " <<< Unable to collect 'git blame' info"
        else:
            yield out


def parse_info_records(lines):
    commits = {}
    in_new_record = False
    for line in lines.splitlines():
        m = uuid_line_re.match(line)
        if m:
            uuid = m.group(1)
            if uuid not in commits:
                record = BlameRecord(uuid)
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

    if os.path.isdir(args.root):
        files = find_modules(args.root)
    elif os.path.isfile(args.root):
        files = iter([args.root])
    else:
        parser.error("Must specify a file or a directory to process")
    blame_infos = collect_blame_info(files)
    for info in blame_infos:
        commits = parse_info_records(info)
        if args.sort_by == 'size':
            sorted_commits = sort_by_size(commits)
        else:
            sorted_commits = sort_by_date(commits)
        limit = None if args.max == 0 else args.max
        top_n = [c.author for c in sorted_commits[:limit]]
        print "(%s)" % ','.join(top_n)
        if args.details:
            for commit in sorted_commits[:limit]:
                print commit.show(args.verbose)


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
                        choices={'date', 'size'}, default='date',
                        help='Sort order for report. Default=date.')
    parser.add_argument(dest='root', metavar='file-or-dir')
    main(parser.parse_args())
