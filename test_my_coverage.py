import pytest

from my_coverage import check_coverage_for_lines
from my_coverage import parse_diffs
from my_coverage import SourceLine
from my_coverage import SourceModule


def test_extract_no_added_line_diffs():
    diffs = """diff --git a/whodunit.py b/whodunit.pyindex acd6edc..513b410 100644
--- a/whodunit.py
+++ b/whodunit.py
@@ -1,3 +1,2 @@
 #!/usr/bin/env python
-# whodunit
 #
"""
    source_file, lines = parse_diffs(diffs)
    expected = [SourceLine(1), SourceLine(2)]
    assert source_file == 'whodunit.py'
    assert lines == expected


def test_extract_single_line_diff():
    diffs = """diff --git a/path/file.py b/path/file.py
index 0fa872e..77ebfef 100644
--- a/path/file.py
+++ b/path/file.py
@@ -59,6 +59,7 @@ INSTANCE_2 = 'testvm2'
 INSTANCE_PC = 'testpcvm'
 INSTANCE_DUAL = 'testdualvm'
 
+NEXUS_BAREMETAL_PORT_1 = 'Ethernet 1/10'
 NEXUS_PORT_1 = 'ethernet:1/10'
 NEXUS_PORT_2 = 'ethernet:1/20'
 NEXUS_DUAL1 = 'ethernet:1/3'
"""
    source_file, lines = parse_diffs(diffs)
    expected = [
        SourceLine(59), SourceLine(60), SourceLine(61),
        SourceLine(62, False),
        SourceLine(63), SourceLine(64), SourceLine(65)
    ]
    assert source_file == 'path/file.py'
    assert lines == expected


def test_extract_multiple_lines():
    diffs = """diff --git a/path/constants.py b/path/constants.py
index 8c57e4a..983de98 100644
--- a/path/constants.py
+++ b/path/constants.py
@@ -42,6 +42,7 @@ PORT_PROFILE_NAME_PREFIX = "OS-PP-"
 CLIENT_PROFILE_NAME_PREFIX = "OS-CL-"
 CLIENT_PROFILE_PATH_PREFIX = "/cl-"
 
-ETH0 = "/ether-eth0"
-ETH1 = "/ether-eth1"
+ETH0 = "eth0"
+ETH1 = "eth1"
+ETH_PREFIX = "/ether-"
 DUPLICATE_EXCEPTION = "object already exists"
"""
    source_file, lines = parse_diffs(diffs)
    expected = [
        SourceLine(42), SourceLine(43), SourceLine(44),
        SourceLine(45, False), SourceLine(46, False), SourceLine(47, False),
        SourceLine(48)
    ]
    assert source_file == 'path/constants.py'
    assert lines == expected


def test_extract_multiple_ranges_for_file():
    """Check multiple ranges in a single file.

    Note: Final region is at end of file and does not have a trailing
    context line.
    """
    diffs = """diff --git a/whodunit.py b/whodunit.py
index 2af698e..79da120 100644
--- a/whodunit.py
+++ b/whodunit.py
@@ -475,8 +484,8 @@ def build_owner(args):
                           args.verbose, args.max)
 
 
-def main(args):
-    args.root = os.path.abspath(args.root)
+def main(parser):
+    args = validate(parser)
     owners = build_owner(args)
 
     # Generators to get the owner info
@@ -491,7 +500,7 @@ def main(args):
         all_authors += top_n
         # Don't alter ordering, as names in sort (date/size) order
         print("(%s)" % ', '.join(top_n))
-        if args.details:
+        if owners.details:
             owners.show_details(args.max)
     print("\\n\\nAll authors: %s" % ', '.join(sort_by_name(all_authors)))
 
@@ -517,5 +526,4 @@ def setup_parser():
     return parser
 
 if __name__ == "__main__":
-    parser = setup_parser()
-    main(parser.parse_args())
+    main(setup_parser())
"""
    source_file, lines = parse_diffs(diffs)
    expected = [
        SourceLine(484), SourceLine(485), SourceLine(486),
        SourceLine(487, False), SourceLine(488, False),
        SourceLine(489), SourceLine(490), SourceLine(491),

        SourceLine(500), SourceLine(501), SourceLine(502),
        SourceLine(503, False),
        SourceLine(504), SourceLine(505), SourceLine(506),

        SourceLine(526), SourceLine(527), SourceLine(528),
        SourceLine(529, False)
    ]
    assert source_file == 'whodunit.py'
    assert len(lines) == 19
    print("%r" % lines)
    print("%r" % expected)
    assert lines == expected


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
    source_file, lines = parse_diffs(diffs)
    assert source_file == 'dummy'
    assert lines == [SourceLine(1, False)]


# TODO(pcm): Tests of input validation and parsing of args


def test_determine_coverage_file_name():
    filename = "relative/path/to/file.py"
    module = SourceModule(filename, lines=[])
    assert module.cover_file == 'relative_path_to_file_py.html'


def test_check_coverage_no_lines():
    coverage_info = """
<p id="n1" class="pln"><a href="#n1">1</a></p>
<p id="n2" class="pln"><a href="#n2">2</a></p>
<p id="n3" class="pln"><a href="#n3">3</a></p>
"""
    lines = []
    updated_lines = check_coverage_for_lines(coverage_info, lines)
    assert updated_lines == lines


def test_check_coverage_multiple_ranges():
    pass


def test_coverage_missing():
    coverage_info = """
<p id="t134" class="pln"><span class="strut">&nbsp;</span></p>
<p id="t135" class="stm mis">&nbsp; &nbsp; &nbsp; &nbsp; <span class="key">return</span> <span class="nam">handle</span><span class="strut">&nbsp;</span></p>
<p id="t136" class="pln"><span class="strut">&nbsp;</span></p>
"""
    lines = [SourceLine(135, is_context=False)]
    check_coverage_for_lines(coverage_info, lines)
    assert lines[0].status == 'mis'
    assert lines[0].code == '    return handle '


def test_coverage_partial():
    pass


def test_coverage_ok():
    pass


def test_coverage_context_line():
    pass
