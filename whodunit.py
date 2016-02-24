# WhoDunIt
#
# Determines the owner(s) of lines in a file. Can operate on a single file
# or directory tree (with results file-by-file). Goal is to use this info
# as a hint on who to contact regarding the file. It collects the counts
# of lines for a commiter, per commit.
#
# Usage:
# whodunit {--when | --size} [--detail] [--max=#] {file | directory-root}
#
# -w, --when     Will list commiters by date (most recent commit first)
# -s, --size     Will list commiters by size of (all of) thier changes
#                with the committer having the largest lines shown first.
# -d, --details  Show detailed info for each file processed
# -m, --max      How many of the top entries to display (default 5)
#
# Output will have file path and name, and then committers, in priority order
# as selected by the options (date/size).
#
# If the --details option is chosen, subsequent lines will show details for
# each committer. In the case of --size, the committer with the most lines
# in all commits, will be shown first, along with the total line count.
#
# In the case of --when, the committer with the commit having the most recent
# date will be shown first, along with the number of lines for that commit.
#

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


class UnableToCollectBlameInfo(Exception):
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

    @property
    def who(self):
        if self.author_mail:
            return self.author_mail
        else:
            return self.author

    @staticmethod
    def date_to_str(time_stamp, time_zone):
        date_time = datetime.datetime.utcfromtimestamp(time_stamp)
        offset_hrs = int(time_zone)/100
        offset_mins = int(time_zone[-2])
        date_time += datetime.timedelta(hours=offset_hrs,
                                        minutes=offset_mins)
        return date_time.strftime('%Y-%m-%d %H:%M:%S ') + time_zone

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

    def __str__(self):
        # TODO(pcm): Change formatting
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


def collect_blame_info(filenames):
    for filename in filenames:
        area, name = os.path.split(filename)
        print "Processing", name
        os.chdir(area)
        p = subprocess.Popen(['git', 'blame', '--line-porcelain', name],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if err:
            raise UnableToCollectBlameInfo("Area %(area)s, file %(file)s",
                                           {'area': area, 'file': name})
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Determine change ownership')
    parser.add_argument('-d', '--details', action='store_true',
                        help='Show details in addition to summary')
    parser.add_argument('-l', '--long', action='store_true',
                        help='Show additional info on each commit')
    parser.add_argument('-s', '--sort', dest='sort_by', action='store',
                        choices={'date', 'size'}, default='date',
                        help='Sort order for report')
    parser.add_argument(dest='root', metavar='file-or-dir')
    args = parser.parse_args()
"""
    files = find_modules("/opt/stack/networking-cisco/networking_cisco"
                         "/plugins/ml2/drivers/cisco/nexus")
    blame_infos = collect_blame_info(files)
    for info in blame_infos:
        commits = parse_info_records(info)
        sorted_commits = sort_by_size(commits)
        for commit in sorted_commits:
            print commit

        sorted_commits = sort_by_date(commits)
        for commit in sorted_commits:
            print commit
"""
