#!/usr/bin/env python
# my_coverage
#
# Indicates the coverage, for lines from the current working directory. It
# assumes that coverage was run on this latest code, and will compare to
# HEAD or HEAD^ (in case you've committed the changes).
#
# Usage:
#    my_coverage.py [-h] repo-dir diff-versions
# Where:
# -h, --help     Show this help message and exit.
# repo-dir       Base directory for the Git repo.
# diff-versions  Commit information to use for diff.
#
# For the diff versions, this should be the input needed to compare
# the changes corresponding to the coverage run data previously collected,
# and previous version.
#
# For committed changes, you can specify 'HEAD^'. For changes that have
# not been committed yet (staged/unstaged), you can specify 'HEAD'.
#
# The output will show the coverage status of lines from the diff, for
# each of the modules.

from __future__ import print_function

import argparse
import os
import re
import subprocess

file_re = re.compile(r'diff --git a/(\S+)')
diff_region_re = re.compile(r'@@\s[-]\S+\s[+](\d+),(\d+)\s@@')


class DiffCollectionFailed(Exception):
    pass


def collect_diffs(root, commits):
    command = ['git', 'diff', '-U1', '-w', commits]
    os.chdir(root)
    print(command)
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if err:
        raise DiffCollectionFailed("In area %s using commits '%s': %s" %
                                   (root, commits, err))
    return iter(out.splitlines())


def make_ranges(lines):
    """Convert list of lines into list of line range tuples.

    Only will be called if there is one or more entries in the list. Single
    lines, will be coverted into tuple with same line.
    """
    print(lines)
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
    print(ranges)
    return ranges

                                                                            
def collect_diff_lines(diff_region, start, last):
    lines = []
    if (last - start) == 1:
        return lines
    line_num = start
    while line_num < last:
        line = diff_region.next()
        if line.startswith('-'):
            continue
        if line.startswith('+'):
            lines.append(line_num)
        line_num += 1
    return lines


def extract_file_diffs(diff_output):
    diff_ranges = []
    for line in diff_output:
        m = file_re.match(line)
        if m:
            source_file = m.group(1)
            continue
        m = diff_region_re.match(line)
        if m:
            start = int(m.group(1))
            last = start + int(m.group(2)) - 1
            lines = collect_diff_lines(diff_output, start, last)
            if lines:
                diff_ranges += make_ranges(lines)
    return (source_file, diff_ranges)


def main(args):
    args.root = os.path.abspath(args.root)
    if not os.path.isdir(args.root):
        parser.error("The repo-dir must be a directory pointing to the top "
                     "of the Git repo")
    if not os.path.isdir(os.path.join(args.root, 'cover')):
        parser.error("Missing cover directory for project")
    diffs = collect_diffs(args.root, args.versions)
    for diff in diffs:
        print(diff)


def setup_parser():
    parser = argparse.ArgumentParser(
        description='Determine ownership for file or tree of files.')
    parser.add_argument(dest='root', metavar='repo-dir')
    parser.add_argument(dest='versions', metavar='versions')
    return parser

if __name__ == "__main__":
    parser = setup_parser()
    main(parser.parse_args())
