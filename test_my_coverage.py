import pytest

import my_coverage


def test_extract_no_diffs():
    diffs = """diff --git a/whodunit.py b/whodunit.pyindex acd6edc..513b410 100644
--- a/whodunit.pyindex
+++ b/whodunit.pyindex
@@ -1,3 +1,2 @@
 #!/usr/bin/env python
-# whodunit
 #
"""
    results = my_coverage.parse_diffs(diffs)
    assert results == ('whodunit.py', [])


def test_extract_single_line_diff():
    diffs = """diff --git a/.coveragerc b/.coveragerc
index b6ce39f..02bd630 100644
--- a/.coveragercindex
+++ b/.coveragercindex
@@ -4,2 +4,3 @@ source = networking_cisco
 omit = networking_cisco/tests/*,networking_cisco/openstack/*
+concurrency = greenlet

"""
    results = my_coverage.parse_diffs(diffs)
    assert results == ('.coveragerc', [(5, 5)])


def test_extract_multiple_lines():
    diffs = """diff --git a/path/constants.py b/path/constants.py
index 8c57e4a..983de98 100644
--- a/path/constants.py
+++ b/path/constants.py
@@ -44,4 +44,5 @@ CLIENT_PROFILE_PATH_PREFIX = "/cl-"

-ETH0 = "/ether-eth0"
-ETH1 = "/ether-eth1"
+ETH0 = "eth0"
+ETH1 = "eth1"
+ETH_PREFIX = "/ether-"
 DUPLICATE_EXCEPTION = "object already exists"
"""
    results = my_coverage.parse_diffs(diffs)
    assert results == ('path/constants.py', [(45, 47)])


def test_extract_multiple_ranges_for_file():
    """Check multiple ranges in a single file.

    Note: Final region is at end of file and does not have a trailing
    context line.
    """
    diffs = """diff --git a/whodunit.py b/whodunit.py
index 2af698e..79da120 100644
--- a/whodunit.py
+++ b/whodunit.py
@@ -465,6 +476,4 @@ def build_owner(args):
         pass
-    elif os.path.isfile(args.root):
+    else:  # File
         args.root, args.filter = os.path.split(args.root)
-    else:
-        parser.error("Must specify a file or a directory to process")
     if args.sort_by == 'date':
@@ -477,4 +486,4 @@ def build_owner(args):
 
-def main(args):
-    args.root = os.path.abspath(args.root)
+def main(parser):
+    args = validate(parser)
     owners = build_owner(args)
@@ -493,3 +502,3 @@ def main(args):
         print("(%s)" % ', '.join(top_n))
-        if args.details:
+        if owners.details:
             owners.show_details(args.max)
@@ -519,3 +528,2 @@ def setup_parser():
 if __name__ == "__main__":
-    parser = setup_parser()
-    main(parser.parse_args())
+    main(setup_parser())
"""
    results = my_coverage.parse_diffs(diffs)
    assert results == ('whodunit.py',
                       [(477, 477), (487, 488), (503, 503), (529, 529)])


def test_extract_file_with_one_line_only():
    """Special case test of file with no context lines available."""
    diffs = """diff --git a/dummy b/dummy
new file mode 100644
index 0000000..257cc56
--- /dev/null
+++ b/dummy
@@ -0,0 +1 @@
+foo
"""
    results = my_coverage.parse_diffs(diffs)
    assert results == ('dummy', [(1, 1)])


# TODO(pcm): Tests of input validation and parsing of args


def test_determine_coverage_file_name():
    filename = "relative/path/to/file.py"
    expected_name = 'relative_path_to_file_py.html'
    assert my_coverage.coverage_file_name(filename) == expected_name
