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
diff_region_re = re.compile(r'@@\s[-]\S+\s[+](\S+)\s@@')


class DiffCollectionFailed(Exception):
    pass


def check_coverage(root, coverage_file, line_ranges):
    """Check the lines in coverage file and report coverage status."""
    pass


def coverage_file_name(source_file):
    return source_file.replace('/', '_').replace('.', '_') + ".html"


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


def collect_diff_lines(diff_region, start, last):
    """Find added lines in a diff region.

    Note: If the region is the last in the file, it may not have a
    trailing context line, so always check, even if there is one or two
    lines.
    """
    lines = []
    line_num = start
    while line_num <= last:
        line = diff_region.next()
        if line.startswith('-'):
            continue
        if line.startswith('+'):
            lines.append(line_num)
        line_num += 1
    return lines


def parse_diffs(diff_output):
    """Collect the file and ranges of diffs added, if any."""
    diff_ranges = []
    source_file = ''
    diff_lines = iter(diff_output.splitlines())
    for line in diff_lines:
        m = file_re.match(line)
        if m:
            source_file = m.group(1)
            continue
        m = diff_region_re.match(line)
        if m:
            start, comma, num = m.group(1).partition(',')
            start = int(start)
            if num:
                last = start + int(num) - 1
            else:
                last = start
            added_lines = collect_diff_lines(diff_lines, start, last)
            if added_lines:
                diff_ranges += make_ranges(added_lines)
    return (source_file, diff_ranges)


def collect_diffs_for_files(root, versions, files):
    """Generator to obtain the diffs for files."""
    os.chdir(root)
    for a_file in files:
        command = ['git', 'diff', '-U1', '-w', versions, '--', a_file]
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if err:
            raise DiffCollectionFailed("Unable to collect diffs for "
                                       "file %s/%s: %s" % (root, a_file, err))
        yield out


def collect_diff_files(root, versions):
    """Generator to obtain all the diff files."""
    command = ['git', 'diff', '--name-only', versions]
    os.chdir(root)
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if err:
        raise DiffCollectionFailed("Unable to find diff files to examine "
                                   "in %s: %s" % (root, err))
    for line in out.splitlines():
        yield line


def main(args):
    args.root = os.path.abspath(args.root)
    if not os.path.isdir(args.root):
        parser.error("The repo-dir must be a directory pointing to the top "
                     "of the Git repo")
    if not os.path.isdir(os.path.join(args.root, 'cover')):
        parser.error("Missing cover directory for project")
    files = collect_diff_files(args.root, args.versions)
    diff_files = collect_diffs_for_files(args.root, args.versions, files)
    for diffs in diff_files:
        source_file, line_ranges = parse_diffs(diffs)
        check_coverage(args.root, source_file, line_ranges)


def setup_parser():
    parser = argparse.ArgumentParser(
        description='Determine ownership for file or tree of files.')
    parser.add_argument(dest='root', metavar='repo-dir',
                        help="Root of Git repo")
    # TODO(pcm): Use -v {commit|working|"string spec"}
    parser.add_argument(dest='versions', help="Git diff version specification")
    return parser


if __name__ == "__main__":
    parser = setup_parser()
    main(parser.parse_args())
