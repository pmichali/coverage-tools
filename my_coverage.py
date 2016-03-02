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
from collections import Counter
import os
import re
import subprocess

file_re = re.compile(r'diff --git a/(\S+)')
diff_region_re = re.compile(r'@@\s[-]\S+\s[+](\S+)\s@@')
source_line_re = re.compile(r'<p id="n(\d+)" class="([^"]+)"')
summary_end_re = re.compile(r'\s+<td class="text">')


class DiffCollectionFailed(Exception):
    pass


class SourceLine(object):

    def __init__(self, line_number, is_context=True, code=''):
        self.line_number = line_number
        self.is_context = is_context
        self.code = code
        self.status = '???'

    def __eq__(self, other):
        return (self.line_number == other.line_number and
                self.is_context == other.is_context)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "SourceLine(line_number=%d, is_context=%s)" % (self.line_number,
                                                              self.is_context)


class SourceModule(object):

    def __init__(self, filename, lines):
        self.filename = filename
        self.lines = lines
        self.line_num_map = {l.line_number: l for l in lines}
        self.cover_file = (filename.replace('/', '_').replace('.', '_') +
                           ".html")
        self.have_report = False

    def update_line_status(self, line_number, status):
        if line_number in self.line_num_map:
            line = self.line_num_map[line_number]
            if status.startswith('pln'):
                line.status = '   '
            else:
                line.status = status[4:7]

    def report(self):
        output = self.filename
        if not self.have_report:
            return "%s (No coverage data)\n" % output
        if not self.lines or all(l.is_context for l in self.lines):
            return "%s (No added/changed lines)\n" % output
        stats = Counter([l.status for l in self.lines if not l.is_context])
        output += " (run={}, mis={}, par={}, ign={})\n".format(
            stats['run'], stats['mis'], stats['par'], stats['   '])
        last_line = None
        for line in self.lines:
            if last_line and line.line_number != (last_line + 1):
                output += "\n"
            output += "{:5d} {} {}{}\n".format(line.line_number,
                                               line.status,
                                               ' ' if line.is_context else '+',
                                               line.code)
            last_line = line.line_number
        return output


def check_coverage_status(coverage_info, module):
    for coverage_line in coverage_info:
        if summary_end_re.match(coverage_line):
            return
        m = source_line_re.match(coverage_line)
        if m:
            line_num = int(m.group(1))
            status = m.group(2)
            module.update_line_status(line_num, status)


def check_coverage_file(root, module):
    """Check the lines in coverage file and report coverage status."""
    report_file = os.path.join(root, 'cover', module.cover_file)
    if not os.path.isfile(report_file):
        return  # No coverage data for file
    with open(report_file) as coverage_info:
        coverage_lines = coverage_info.readlines()
        check_coverage_status(coverage_lines, module)
        module.have_report = True


def collect_diff_lines(diff_region, start, last):
    """Find added and context lines in a diff region.

    Note: If the diff region is at the start or end of the file, there
    may not be context lines.
    """
    lines = []
    line_num = start
    while line_num <= last:
        line = diff_region.next()
        if line.startswith('-'):
            continue
        lines.append(SourceLine(line_num, is_context=line.startswith(' '),
                                code=line[1:]))
        line_num += 1
    return lines


def parse_diffs(diff_output):
    """Collect the file and ranges of diffs added, if any."""
    added_lines = []
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
            added_lines += collect_diff_lines(diff_lines, start, last)
    return (source_file, added_lines)


def collect_diffs_for_files(root, versions, source_files):
    """Generator to obtain the diffs for files."""
    os.chdir(root)
    for filename in source_files:
        command = ['git', 'diff', '-U3', '-w', versions, '--', filename]
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diff_lines, err = p.communicate()
        if err:
            raise DiffCollectionFailed(
                "Unable to collect diffs for file %s/%s: %s" %
                (root, filename, err))
        yield diff_lines


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
    for filename in out.splitlines():
        if not os.path.basename(filename).startswith('.'):
            yield filename


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
        source_file, lines = parse_diffs(diffs)
        module = SourceModule(source_file, lines)
        check_coverage_file(args.root, module)
        print(module.report())

def setup_parser():
    parser = argparse.ArgumentParser(
        description='Determine ownership for file or tree of files.')
    parser.add_argument(dest='root', metavar='repo-dir',
                        help="Root of Git repo")
    # TODO(pcm): Use --version {latest|working|"string spec"}
    # TODO(pcm): --details, show lines of code
    parser.add_argument(dest='versions', help="Git diff version specification")
    return parser


if __name__ == "__main__":
    parser = setup_parser()
    main(parser.parse_args())
