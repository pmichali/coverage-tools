import mock
import os
import shutil
import subprocess
import tempfile
from my_coverage import check_coverage_file
from my_coverage import collect_diff_files
from my_coverage import collect_diffs_for_files
from my_coverage import DiffCollectionFailed
from my_coverage import setup_parser
from my_coverage import validate


@pytest.fixture()
def fake_cover_project(request):
    cover_project_area = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(cover_project_area)
    os.mkdir('cover')
    os.chdir(cwd)

    def fin():
        shutil.rmtree(cover_project_area)
    request.addfinalizer(fin)
    return cover_project_area


@pytest.fixture()
def fake_project(request):
    project_area = tempfile.mkdtemp()

    def fin():
        shutil.rmtree(project_area)
    request.addfinalizer(fin)
    return project_area
    assert lines == [SourceLine(1, is_context=False)]


def test_extract_no_context_no_added_lines():
    """Context is set to zero and there are no added lines."""
    diffs = """diff --git a/dummy b/dummy
index 7a47da8..7ee1d92 100644
--- a/dummy
+++ b/dummy
@@ -65 +35,0 @@ check_pot_files_errors () {
-check_opinionated_shell
"""
    source_file, lines = parse_diffs(diffs)
    assert source_file == 'dummy'
    assert lines == []


def test_extract_one_line_deleted_and_added():
    """Special case where both diff markers have no commas.

    Indicates that one line deleted and one line added.
    """
    diffs = """diff --git a/devstack/saf/cisco_saf b/devstack/saf/cisco_saf
index 2498062..efcc602 100644
--- a/devstack/saf/cisco_saf
+++ b/devstack/saf/cisco_saf
@@ -1 +1 @@
-#!/bin/bash
+#!/usr/bin/env bash
"""
    source_file, lines = parse_diffs(diffs)
    assert source_file == 'devstack/saf/cisco_saf'
    assert lines == [SourceLine(1, is_context=False)]


def test_collecting_diffs(monkeypatch):
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.side_effect = [('output1', ''),
                                                      ('output2', '')]
        monkeypatch.setattr('os.chdir', lambda x: None)
        diffs = collect_diffs_for_files('/some/path', versions="HEAD",
                                        source_files=['foo', 'bar'],
                                        context_lines=5)
        assert list(diffs) == ['output1', 'output2']

    expected = [
        mock.call(['git', 'diff', '-U5', '-w', 'HEAD', '--', 'foo'],
                  stderr=-1, stdout=-1),
        mock.call().communicate(),
        mock.call(['git', 'diff', '-U5', '-w', 'HEAD', '--', 'bar'],
                  stderr=-1, stdout=-1),
        mock.call().communicate()
    ]
    assert popen.call_count == 2
    popen.assert_has_calls(expected)
def test_fail_collecting_diffs(monkeypatch):
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.return_value = ('', 'bad file')
        monkeypatch.setattr('os.chdir', lambda x: None)

        diffs = collect_diffs_for_files('/some/path', versions="HEAD",
                                        source_files=['foo'],
                                        context_lines=5)
        with pytest.raises(DiffCollectionFailed) as excinfo:
            for diff in diffs:
                pass
        expected_msg = ('Unable to collect diffs for file /some/path/foo: '
                        'bad file')
        assert excinfo.value.message == expected_msg


def test_collecting_diff_files(monkeypatch):
    """Ignores files with leading period."""
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.return_value = (
            'foo.py\n.ignored-file\nbar.py\n', '')
        monkeypatch.setattr('os.chdir', lambda x: None)

        diff_files = collect_diff_files(fake_project, 'HEAD')
        assert list(diff_files) == ['foo.py', 'bar.py']


def test_fail_collecting_diff_files(monkeypatch):
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.return_value = ('foo.py', 'no file')
        monkeypatch.setattr('os.chdir', lambda x: None)
        
        diff_files = collect_diff_files('/some/path', 'HEAD')
        with pytest.raises(DiffCollectionFailed) as excinfo:
            for diff_file in diff_files:
                pass
        expected_msg = ('Unable to find diff files to examine in '
                        '/some/path: no file')
        assert excinfo.value.message == expected_msg
""".splitlines()
def test_coverage_status_collection():
...
<title>Coverage for foo.py: 81%</title>
...
...
            </td>
            <td class="text">
""".splitlines()
    assert module.coverage == '81%'


def test_missing_coverage_file(fake_cover_project):
    module = SourceModule('foo.py', [])
    check_coverage_file(fake_cover_project, module)
    assert not module.have_report


def test_checking_coverage_file(monkeypatch):
    coverage_info = """
...
<title>Coverage for foo.py: 5%</title>
...
<p id="n2" class="stm run"><a href="#n2">2</a></p>
...
            </td>
            <td class="text">
""".splitlines()
    line = SourceLine(2, is_context=False)
    module = SourceModule('foo.py', [line])

    def is_a_file(filename):
        return True
    monkeypatch.setattr(os.path, 'isfile', is_a_file)

    with mock.patch('__builtin__.open',
                    mock.mock_open(), create=True) as mock_open:
        mock_open.return_value.readlines.return_value = coverage_info
        check_coverage_file('.', module)
    assert module.have_report
    assert line.status == 'run'
    assert module.coverage == '5%'


def test_report_non_coverage_files():
    module = SourceModule('path/foo.py', [])
    assert module.report() == 'path/foo.py (No coverage data)\n'


def test_report_no_no_added_lines():
    module = SourceModule('path/foo.py', [])
    module.have_report = True
    assert module.report() == 'path/foo.py (No added/changed lines)\n'

    lines = [SourceLine(10, is_context=True), SourceLine(12, is_context=True)]
    module = SourceModule('deleted_lines_file', lines)
    module.have_report = True
    assert module.report() == 'deleted_lines_file (No added/changed lines)\n'


def test_report_one_line():
    line = SourceLine(10, is_context=False, code='    x = 1')
    module = SourceModule('path/foo.py', [line])
    module.have_report = True
    module.coverage = '100%'
    line.status = 'run'
    expected = """path/foo.py (run=1, mis=0, par=0, ign=0) 100%
   10 run +    x = 1
"""
    assert module.report() == expected


def test_report_multiple_blocks():
    lines = [SourceLine(10, is_context=False, code='    x = 1'),
             SourceLine(11, is_context=False, code='    y = 2'),
             SourceLine(20, is_context=False, code='    z = 3'),
             SourceLine(21, is_context=False, code='    for i in range(5)')]
    lines[0].status = 'run'
    lines[1].status = 'mis'
    lines[2].status = 'par'
    lines[3].status = '   '
    module = SourceModule('path/foo.py', lines)
    module.have_report = True
    module.coverage = '50%'

    expected = """path/foo.py (run=1, mis=1, par=1, ign=1) 50%
   10 run +    x = 1
   11 mis +    y = 2

   20 par +    z = 3
   21     +    for i in range(5)
"""
    assert module.report() == expected


def test_argument_parse_which(fake_cover_project):
    parser = setup_parser()
    args = validate(parser, [fake_cover_project])
    assert args.commits == 'HEAD'
    args = validate(parser, ['-w', 'working', fake_cover_project])
    assert args.commits == 'HEAD'
    args = validate(parser, ['-w', 'committed', fake_cover_project])
    assert args.commits == 'HEAD^..HEAD'
    args = validate(parser, ['-w', 'HEAD~5..HEAD~3', fake_cover_project])
    assert args.commits == 'HEAD~5..HEAD~3'


def test_argument_parse_context(fake_cover_project):
    parser = setup_parser()
    args = validate(parser, ['-c', '10', fake_cover_project])
    assert args.context == 10


def test_validate_directory(fake_cover_project):
    parser = setup_parser()
    assert validate(parser, [fake_cover_project])


def test_validate_no_coverage_area(fake_project):
    parser = setup_parser()
    with pytest.raises(SystemExit) as excinfo:
        validate(parser, [fake_project])
    assert str(excinfo.value) == '2'


def test_validate_no_directory():
    parser = setup_parser()
    with pytest.raises(SystemExit) as excinfo:
        validate(parser, ['bogus-dir'])
    assert str(excinfo.value) == '2'