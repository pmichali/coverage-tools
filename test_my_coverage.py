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
""".splitlines()
    results = my_coverage.extract_file_diffs(iter(diffs))
    assert results == ('whodunit.py', [])


def test_extract_single_line_diff():
    diffs = """diff --git a/.coveragerc b/.coveragerc
index b6ce39f..02bd630 100644
--- a/.coveragercindex
+++ b/.coveragercindex
@@ -4,2 +4,3 @@ source = networking_cisco
 omit = networking_cisco/tests/*,networking_cisco/openstack/*
+concurrency = greenlet

""".splitlines()
    results = my_coverage.extract_file_diffs(iter(diffs))
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
""".splitlines()
    results = my_coverage.extract_file_diffs(iter(diffs))
    assert results == ('path/constants.py', [(45, 47)])



def test_extract_multiple_ranges_for_file():
    pass

