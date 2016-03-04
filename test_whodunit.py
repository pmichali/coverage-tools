import copy
import mock
import os
import pytest
import shutil
import subprocess
import tempfile
import whodunit


line_one = """6e3b3aec8a73da4129e83554ad5ac2f43d4ec775 1813 1794 1794
author Carol Coverage
author-mail <carolb@example.com>
author-time 1453922613
author-tz -0500
committer Carol Coverage
committer-mail <carolb@example.com>
committer-time 1454335722
committer-tz -0500
summary Baremetal-Ironic development for Nexus ML2 drivers
previous 25088fc1e98735e811e6bac8c9930d44639130b9 networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
filename networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
\t\t\tfor switch_ip, attr2, attr3, attr4 in host_connections:
"""

line_two = """65491efbd9ea0843c00cb50ff4c89211862924de 790 1795
author Rich Rocket
author-mail <richard@cover.net>
author-time 1426193499
author-tz -0400
committer richard
committer-mail <richard@cover.net>
committer-time 1427468897
committer-tz +0000
summary ML2 cisco_nexus MD: Sync of staging/junoplus
previous 495251e5c9d6a329ebe1631b1524a98b81ee76e6 networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
filename networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
                            physnet = self._nexus_switches.get((switch_ip, 'physnet'))
"""

line_three = """6e3b3aec8a73da4129e83554ad5ac2f43d4ec775 28 28 1
author Carol Coverage
author-mail <carolb@example.com>
author-time 1453922613
author-tz -0500
committer Carol Coverage
committer-mail <carolb@example.com>
committer-time 1454335722
committer-tz -0500
summary Baremetal-Ironic development for Nexus ML2 drivers
previous 25088fc1e98735e811e6bac8c9930d44639130b9 networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
filename networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
\tfrom oslo_serialization import jsonutils
"""


@pytest.fixture()
def fake_project(request):
    project_area = tempfile.mkdtemp()

    def fin():
        shutil.rmtree(project_area)
    request.addfinalizer(fin)
    return project_area


def test_no_filter_for_line_ranges():
    assert whodunit.Owners.build_line_range_filter([]) == []


def test_filter_one_range():
    assert whodunit.Owners.build_line_range_filter([(5, 5)]) == ['-L 5,5']


def test_filter_multiple_ranges():
    result = whodunit.Owners.build_line_range_filter([(1, 3), (6, 7), (9, 9)])
    assert result == ['-L 1,3', '-L 6,7', '-L 9,9']


def test_build_valid_record():
    record = whodunit.BlameRecord('some-uuid', 1)
    record.store_attribute('author', 'Me')
    record.store_attribute('author-mail', 'foo@bar.net')
    record.store_attribute('author-time', '1391791021')
    record.store_attribute('author-tz', '-0500')
    record.store_attribute('committer', 'You')
    record.store_attribute('committer-mail', 'you@bar.net')
    record.store_attribute('committer-time', '1454335722')
    record.store_attribute('committer-tz', '-0500')
    assert record.validate() is None


def test_committer_date_formatting():
    record = whodunit.BlameRecord('some-uuid', 5)
    record.store_attribute('committer-time', '1391791021')
    record.store_attribute('committer-tz', '-0500')
    assert record.date == '2014-02-07 11:37:01 -0500'


def test_ignoring_blame_info():
    record = whodunit.BlameRecord('some-uuid', 10)
    record.store_attribute('summary', 'do not store summary')
    assert not hasattr(record, 'summary')
    record.store_attribute('filename', 'do not store file info')
    assert not hasattr(record, 'filename')
    record.store_attribute('previous', 'do not store previous commit info')
    assert not hasattr(record, 'previous')


def test_fail_record_missing_author():
    record = whodunit.BlameRecord('some-uuid', 3)
    record.store_attribute('author-mail', 'foo@bar.net')
    record.store_attribute('author-time', '1391791021')
    record.store_attribute('author-tz', '-0500')
    record.store_attribute('committer', 'You')
    record.store_attribute('committer-mail', 'you@bar.net')
    record.store_attribute('committer-time', '1454335722')
    record.store_attribute('committer-tz', '-0500')
    with pytest.raises(whodunit.BadRecordException) as e:
        record.validate()
    assert e.value.message == "Missing author name"


def test_fail_record_missing_committer():
    record = whodunit.BlameRecord('some-uuid', 5)
    record.store_attribute('author', 'Me')
    record.store_attribute('author-mail', 'foo@bar.net')
    record.store_attribute('author-time', '1391791021')
    record.store_attribute('author-tz', '-0500')
    record.store_attribute('committer-mail', 'you@bar.net')
    record.store_attribute('committer-time', '1454335722')
    record.store_attribute('committer-tz', '-0500')
    with pytest.raises(whodunit.BadRecordException) as e:
        record.validate()
    assert e.value.message == "Missing committer name"


def test_fail_record_missing_author_time():
    record = whodunit.BlameRecord('some-uuid', 2)
    record.store_attribute('author', 'Me')
    record.store_attribute('author-mail', 'foo@bar.net')
    record.store_attribute('author-tz', '-0500')
    record.store_attribute('committer', 'You')
    record.store_attribute('committer-mail', 'you@bar.net')
    record.store_attribute('committer-time', '1454335722')
    record.store_attribute('committer-tz', '-0500')
    with pytest.raises(whodunit.BadRecordException) as e:
        record.validate()
    assert e.value.message == "Missing author time information"

    record = whodunit.BlameRecord('some-uuid', 3)
    record.store_attribute('author', 'Me')
    record.store_attribute('author-mail', 'foo@bar.net')
    record.store_attribute('author-time', '1391791021')
    record.store_attribute('committer', 'You')
    record.store_attribute('committer-mail', 'you@bar.net')
    record.store_attribute('committer-time', '1454335722')
    record.store_attribute('committer-tz', '-0500')
    with pytest.raises(whodunit.BadRecordException) as e:
        record.validate()
    assert e.value.message == "Missing author time information"


def test_fail_record_missing_committer_time():
    record = whodunit.BlameRecord('some-uuid', 8)
    record.store_attribute('author', 'Me')
    record.store_attribute('author-mail', 'foo@bar.net')
    record.store_attribute('author-time', '1391791021')
    record.store_attribute('author-tz', '-0500')
    record.store_attribute('committer', 'You')
    record.store_attribute('committer-mail', 'you@bar.net')
    record.store_attribute('committer-tz', '-0500')
    with pytest.raises(whodunit.BadRecordException) as e:
        record.validate()
    assert e.value.message == "Missing committer time information"

    record = whodunit.BlameRecord('some-uuid', 9)
    record.store_attribute('author', 'Me')
    record.store_attribute('author-mail', 'foo@bar.net')
    record.store_attribute('author-time', '1391791021')
    record.store_attribute('author-tz', '-0500')
    record.store_attribute('committer', 'You')
    record.store_attribute('committer-mail', 'you@bar.net')
    record.store_attribute('committer-time', '1454335722')
    with pytest.raises(whodunit.BadRecordException) as e:
        record.validate()
    assert e.value.message == "Missing committer time information"


def test_fail_record_missing_author_email():
    record = whodunit.BlameRecord('some-uuid', 1)
    record.store_attribute('author', 'Me')
    record.store_attribute('author-time', '1391791021')
    record.store_attribute('author-tz', '-0500')
    record.store_attribute('committer', 'You')
    record.store_attribute('committer-mail', 'you@bar.net')
    record.store_attribute('committer-time', '1454335722')
    record.store_attribute('committer-tz', '-0500')
    with pytest.raises(whodunit.BadRecordException) as e:
        record.validate()
    assert e.value.message == "Missing author email"


def test_fail_record_missing_committer_email():
    record = whodunit.BlameRecord('some-uuid', 1)
    record.store_attribute('author', 'Me')
    record.store_attribute('author-mail', 'foo@bar.net')
    record.store_attribute('author-time', '1391791021')
    record.store_attribute('author-tz', '-0500')
    record.store_attribute('committer', 'You')
    record.store_attribute('committer-time', '1454335722')
    record.store_attribute('committer-tz', '-0500')
    with pytest.raises(whodunit.BadRecordException) as e:
        record.validate()
    assert e.value.message == "Missing committer email"


def test_parsing_for_two_commits():
    blame_output = line_one + line_two
    owners = whodunit.Owners(".")
    commits = owners.parse_info_records(blame_output)
    assert len(commits) == 2
    record = commits[0]
    assert record.uuid == "6e3b3aec8a73da4129e83554ad5ac2f43d4ec775"
    assert record.line_number == 1794
    assert record.line_count == 1
    assert record.author == "Carol Coverage"
    assert record.date == "2016-02-01 09:08:42 -0500"
    assert record.author_mail == "<carolb@example.com>"
    record = commits[1]
    assert record.uuid == "65491efbd9ea0843c00cb50ff4c89211862924de"
    assert record.line_number == 1795
    assert record.line_count == 1
    assert record.author == "Rich Rocket"
    assert record.date == "2015-03-27 15:08:17 +0000"
    assert record.author_mail == "<richard@cover.net>"


def test_parse_two_records_same_commit():
    blame_output = line_one + line_three
    owners = whodunit.Owners(".")
    commits = owners.parse_info_records(blame_output)
    assert len(commits) == 1
    record = commits[0]
    assert record.uuid == "6e3b3aec8a73da4129e83554ad5ac2f43d4ec775"
    assert record.line_count == 2
    assert record.author == "Carol Coverage"
    assert record.date == "2016-02-01 09:08:42 -0500"
    assert record.author_mail == "<carolb@example.com>"


def test_parse_not_aggregating_two_records_same_commit():
    blame_output = line_one + line_three
    owners = whodunit.CoverageOwners(".")
    commits = owners.parse_info_records(blame_output)
    assert len(commits) == 2
    record = commits[0]
    assert record.uuid == "6e3b3aec8a73da4129e83554ad5ac2f43d4ec775"
    assert record.line_number == 1794
    assert record.line_count == 1
    assert record.author == "Carol Coverage"
    assert record.date == "2016-02-01 09:08:42 -0500"
    assert record.author_mail == "<carolb@example.com>"
    record = commits[1]
    assert record.uuid == "6e3b3aec8a73da4129e83554ad5ac2f43d4ec775"
    assert record.line_number == 28
    assert record.line_count == 1
    assert record.author == "Carol Coverage"
    assert record.date == "2016-02-01 09:08:42 -0500"
    assert record.author_mail == "<carolb@example.com>"


def create_commit(info):
    """Helper to create a dummy commit record."""
    commit = whodunit.BlameRecord(info['uuid'], 5)
    commit.line_count = info['lines'] if 'lines' in info else 10
    commit.line_number = info['line_number'] if 'line_number' in info else 1
    # For testing, we set the calculated line range equal to the line number
    commit.lines = str(commit.line_number)
    commit.author = info['author'] if 'author' in info else 'Joe Dirt'
    commit.author_mail = (info['author_mail'] if 'author_mail' in info
                          else 'joe@dirt.com')
    commit.author_time = (info['author_time'] if 'author_time' in info
                          else 1453922613)
    commit.author_tz = '-0500'
    commit.committer = (info['committer'] if 'committer' in info
                        else commit.author)
    commit.committer_mail = (info['committer_mail'] if 'committer_mail' in info
                             else commit.author_mail)
    commit.committer_time = (info['committer_time'] if 'committer_time' in info
                             else 1454335722)
    commit.committer_tz = '-0500'
    return commit


def test_merge_only_one_commit():
    commit1 = create_commit({'uuid': 'uuid-1'})
    commit = whodunit.SizeOwners.merge_user_commits([commit1])
    assert commit == commit1


def test_merge_two_commits_from_same_author():
    commit1 = create_commit({'uuid': 'uuid-1'})
    commit2 = create_commit({'uuid': 'uuid-2'})
    commit = whodunit.SizeOwners.merge_user_commits([commit1, commit2])
    assert commit.line_count == 20
    assert commit.date == '2016-02-01 09:08:42 -0500'
    assert commit.uuid == 'uuid-1'

def test_merge_two_with_second_newer():
    commit1 = create_commit({'uuid': 'uuid-1', 'committer_time': 1453922613})
    commit2 = create_commit({'uuid': 'uuid-2', 'committer_time': 1456193499})
    commit = whodunit.SizeOwners.merge_user_commits([commit1, commit2])
    assert commit.line_count == 20
    assert commit.date == '2016-02-22 21:11:39 -0500'
    assert commit.uuid == 'uuid-2'


def test_report_by_size():
    """Test reporting by number of lines for a user.

    Aggregates commits for the same author. Will show the date of the most
    recent commit for the author, when they have multiple commits.
    """
    commit1 = create_commit({'uuid': 'uuid-1', 'lines': 50})
    info = {'uuid': 'uuid-2', 'lines': 100,
            'author': 'Carl Coder', 'author_mail': 'carl@bad-code.com',
            'author_time': 1426193499, 'commiter_time': 1427468897}
    commit2 = create_commit(info)
    info = {'uuid': 'uuid-3', 'lines': 60, 'committer_time': 1456193499}
    commit3 = create_commit(info)

    owners = whodunit.SizeOwners(".")
    owners.commits = [commit1, commit2, commit3]
    sorted_commits = owners.sort()
    assert len(sorted_commits) == 2

    first = sorted_commits[0]
    assert first.uuid == 'uuid-3'  # Newest commit
    assert first.author == 'Joe Dirt'
    assert first.author_mail == 'joe@dirt.com'
    assert first.line_count == 110  # Aggregate of all lines
    assert first.date == '2016-02-22 21:11:39 -0500'

    second = sorted_commits[1]
    assert second.uuid == 'uuid-2'
    assert second.author == 'Carl Coder'
    assert second.author_mail == 'carl@bad-code.com'
    assert second.line_count == 100
    assert second.date == '2016-02-01 09:08:42 -0500'


def test_report_by_date():
    """Test reporting by date of commit.

    Can be multiple outputs for a single user, if they have more than one
    commit.
    """
    commit1 = create_commit({'uuid': 'uuid-1', 'committer_time': 1453922613})
    commit2 = create_commit({'uuid': 'uuid-2', 'committer_time': 1454335722})
    commit3 = create_commit({'uuid': 'uuid-3', 'committer_time': 1452193499})
    owners = whodunit.DateOwners(".")
    owners.commits = [commit1, commit2, commit3]
    sorted_commits = owners.sort()
    assert len(sorted_commits) == 3
    assert sorted_commits == [commit2, commit1, commit3]


def test_build_range_of_one_line():
    assert whodunit.CoverageOwners.make_ranges([1]) == [(1, 1)]


def test_build_one_range():
    assert whodunit.CoverageOwners.make_ranges([10, 11, 12]) == [(10, 12)]


def test_build_multiple_ranges():
    expected = [(1, 2), (4, 5), (7, 7)]
    assert whodunit.CoverageOwners.make_ranges([1, 2, 4, 5, 7]) == expected


def test_coverage_ok():
    """No file to process, as coverage is 100%."""
    coverage_fragment = """
<title>Coverage for some/path/to/some_file.py: 100%</title>

<p id="n203" class="stm run hide_run"><a href="#n203">203</a></p>
<p id="n204" class="stm run hide_run"><a href="#n204">204</a></p>
<p id="n205" class="pln"><a href="#n205">205</a></p>

            </td>
            <td class="text">
""".splitlines()
    result = whodunit.CoverageOwners.determine_coverage(coverage_fragment)
    assert result == ('', [])


def test_coverage_lacking_for_one_line():
    coverage_fragment = """
<title>Coverage for some/path/to/some_file.py: 82%</title>

<p id="n188" class="pln"><a href="#n188">188</a></p>
<p id="n189" class="stm mis"><a href="#n189">189</a></p>
<p id="n190" class="pln"><a href="#n190">190</a></p>

            </td>
            <td class="text">
""".splitlines()
    result = whodunit.CoverageOwners.determine_coverage(coverage_fragment)
    assert result == ("some/path/to/some_file.py", [(189, 189)])


def test_coverage_lacking_for_a_range_of_lines():
    """One range of lines that are missing coverage or partial covered."""
    coverage_fragment = """
<title>Coverage for some/path/to/some_file.py: 82%</title>

<p id="n160" class="pln"><a href="#n160">160</a></p>
<p id="n161" class="stm mis"><a href="#n161">161</a></p>
<p id="n162" class="stm mis"><a href="#n162">162</a></p>
<p id="n163" class="stm mis"><a href="#n163">163</a></p>

            </td>
            <td class="text">
""".splitlines()
    result = whodunit.CoverageOwners.determine_coverage(coverage_fragment)
    assert result == ("some/path/to/some_file.py", [(161, 163)])


def test_coverage_lacking_for_several_ranges():
    """Several ranges of missing/partial coverage."""
    coverage_fragment = """
<title>Coverage for some/path/to/some_file.py: 82%</title>

<p id="n103" class="stm run hide_run"><a href="#n103">103</a></p>
<p id="n104" class="stm mis"><a href="#n104">104</a></p>
<p id="n105" class="stm mis"><a href="#n105">105</a></p>
<p id="n106" class="stm mis"><a href="#n106">106</a></p>
<p id="n107" class="pln"><a href="#n107">107</a></p>
<p id="n108" class="pln"><a href="#n108">108</a></p>
<p id="n109" class="stm mis"><a href="#n109">109</a></p>

<p id="n289" class="pln"><a href="#n289">289</a></p>
<p id="n290" class="stm par run hide_run"><a href="#n290">290</a></p>
<p id="n291" class="stm mis"><a href="#n291">291</a></p>
<p id="n292" class="pln"><a href="#n292">292</a></p>

            </td>
            <td class="text">
""".splitlines()
    result = whodunit.CoverageOwners.determine_coverage(coverage_fragment)
    assert result == ("some/path/to/some_file.py",
                      [(104, 106), (109, 109), (290, 291)])


def test_parsing_date_options():
    parser = whodunit.setup_parser()
    args = parser.parse_args(['-s', 'date', 'dummy-file'])
    assert args.sort_by == 'date'
    assert not args.verbose
    assert not args.details
    assert args.filter == "*"
    assert args.max == 0


def test_parsing_size_with_verbose_details_and_limit():
    parser = whodunit.setup_parser()
    args = parser.parse_args(['-s', 'size', '-d', '-v', '-m', "5",
                              '-f', '*.py', 'dummy-file'])
    assert args.sort_by == 'size'
    assert args.verbose
    assert args.details
    assert args.filter == "*.py"
    assert args.max == 5


def test_parsing_coverage_options():
    parser = whodunit.setup_parser()
    args = parser.parse_args(['-s', 'cover', 'dummy-file'])
    assert args.sort_by == 'cover'
    assert not args.verbose
    assert not args.details
    assert args.filter == "*"
    assert args.max == 0


def test_validate_cover():
    parser = whodunit.setup_parser()
    args = whodunit.validate(parser, ['-s', 'cover', '.'])
    assert args.sort_by == 'cover'


def test_validate_with_directory():
    parser = whodunit.setup_parser()
    args = whodunit.validate(parser, ['-s', 'date', '.'])
    assert args.sort_by == 'date'


def test_validate_with_file():
    parser = whodunit.setup_parser()
    args = whodunit.validate(parser, ['-s', 'size', './test_whodunit.py'])
    assert args.sort_by == 'size'


def test_fail_validate_cover_not_directory():
    parser = whodunit.setup_parser()
    with pytest.raises(SystemExit) as excinfo:
        whodunit.validate(parser, ['-s', 'cover', './test_whodunit.py'])
    assert str(excinfo.value) == '2'


def test_fail_validate_cover_missing_coverage_directory(fake_project):
    parser = whodunit.setup_parser()
    with pytest.raises(SystemExit) as excinfo:
        whodunit.validate(parser, ['-s', 'cover', fake_project])
    assert str(excinfo.value) == '2'


def test_fail_validate_cover_with_max():
    parser = whodunit.setup_parser()
    with pytest.raises(SystemExit) as excinfo:
        whodunit.validate(parser, ['-s', 'cover', '-m', '5', '.'])
    assert str(excinfo.value) == '2'


def test_fail_validate_not_dir_or_file():
    parser = whodunit.setup_parser()
    with pytest.raises(SystemExit) as excinfo:
        whodunit.validate(parser, ['-s', 'date', './bogus-file'])
    assert str(excinfo.value) == '2'


def test_build_date_owner():
    parser = whodunit.setup_parser()
    args = whodunit.validate(parser, ['-s', 'date', '.'])
    owner = whodunit.build_owner(args)
    assert isinstance(owner, whodunit.DateOwners)


def test_build_size_owner():
    parser = whodunit.setup_parser()
    args = whodunit.validate(parser, ['-s', 'size', './test_whodunit.py'])
    owner = whodunit.build_owner(args)
    assert isinstance(owner, whodunit.SizeOwners)


def test_build_coverage_owner():
    parser = whodunit.setup_parser()
    args = whodunit.validate(parser, ['-s', 'cover', '.'])
    owner = whodunit.build_owner(args)
    assert isinstance(owner, whodunit.CoverageOwners)


def test_show_commit():
    commit = create_commit(
        {'uuid': '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775'})
    expected_output = "    6e3b3aec    10 Joe Dirt                  2016-02-01"
    owners = whodunit.Owners(".")
    assert owners.show(commit) == expected_output


def test_show_commit_verbose_mode():
    info = {'uuid': '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775',
            'committer': 'Patty Python', 'committer_mail': 'patty.python.com'}
    commit = create_commit(info)
    expected_output = ("    6e3b3aec    10 "
                       "Joe Dirt joe@dirt.com                              "
                       "2016-02-01 09:08:42 -0500 "
                       "Patty Python patty.python.com")
    owners = whodunit.Owners(".", verbose=True)
    assert owners.show(commit) == expected_output


def test_show_commit_for_coverage():
    commit1 = create_commit(
        {'uuid': '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775',
         'lines': 1})
    commit2 = create_commit(
        {'uuid': '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775',
         'lines': 1, 'line_number': 3, 'committer_time': 1453922613})
    commit3 = create_commit(
        {'uuid': '65491efbd9ea0843c00cb50ff4c89211862924de',
         'lines': 1, 'line_number': 5, 'committer_time': 1427468897,
         'author': 'Patty Python'})
    owners = whodunit.CoverageOwners(".")
    expected_output = ("    6e3b3aec           1 Joe Dirt                  "
                       "2016-02-01")
    assert owners.show(commit1) == expected_output
    expected_output = ("    6e3b3aec           3 Joe Dirt                  "
                       "2016-01-27")
    assert owners.show(commit2) == expected_output
    expected_output = ("    65491efb           5 Patty Python              "
                       "2015-03-27")
    assert owners.show(commit3) == expected_output


def test_show_commit_for_coverage_verbose():
    info = {'uuid': '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775',
            'lines': 1, 'line_number': 1547,
            'committer': 'Patty Python', 'committer_mail': 'patty.python.com'}
    commit = create_commit(info)
    expected_output = ("    6e3b3aec        1547 "
                       "Joe Dirt joe@dirt.com                              "
                       "2016-02-01 09:08:42 -0500 "
                       "Patty Python patty.python.com")
    owners = whodunit.CoverageOwners(".", verbose=True)
    assert owners.show(commit) == expected_output


def test_name_sort():
    names = set(['Charlie Coder', 'Zebra Able'])
    assert whodunit.sort_by_name(names) == ['Zebra Able', 'Charlie Coder']

    names = set(['Peter', 'Paul', 'Mary'])
    assert whodunit.sort_by_name(names) == ['Mary', 'Paul', 'Peter']

    names = set(['Peter', 'paul', 'Mary'])
    assert whodunit.sort_by_name(names) == ['Mary', 'paul', 'Peter']

    names = set(['Joe Zoolander', 'Charlie Coder', 'Xanadu'])
    expected = ['Charlie Coder', 'Xanadu', 'Joe Zoolander']
    assert whodunit.sort_by_name(names) == expected

    names = set(['Xanadu', 'Charlie Z. Coder', 'Joe A. Zoolander'])
    expected = ['Charlie Z. Coder', 'Xanadu', 'Joe A. Zoolander']
    assert whodunit.sort_by_name(names) == expected

    names = set(['Marky Malarkie', 'Joe Dirt Sr.'])
    expected = ['Marky Malarkie', 'Joe Dirt Sr.']  # doesn't handle suffix
    assert whodunit.sort_by_name(names) == expected

    names = set(['john', 'Patty Python', 'Charlie Coder'])
    expected = ['Charlie Coder', 'john', 'Patty Python']
    assert whodunit.sort_by_name(names) == expected


def test_unique_authors():
    UUID1 = '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775'
    UUID2 = '65491efbd9ea0843c00cb50ff4c89211862924de'
    commit1 = create_commit({'uuid': UUID1, 'lines': 1})
    commit2 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 2})
    commit3 = create_commit({'uuid': UUID2, 'lines': 1, 'line_number': 5,
                             'committer_time': 1427468897,
                             'author': 'Patty Python'})
    owners = whodunit.Owners(".")
    owners.sorted_commits = [commit1, commit2, commit3]
    authors = owners.unique_authors(0)
    assert authors == ['Joe Dirt', 'Patty Python']


def test_no_commits():
    owners = whodunit.CoverageOwners(".")
    actual_commits = owners.sort()
    assert actual_commits == []


def test_one_commit():
    UUID1 = '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775'
    commit = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 1})
    expected = copy.copy(commit)
    expected.lines = '1'
    owners = whodunit.CoverageOwners(".")
    owners.commits = [commit]
    actual_commits = owners.sort()
    assert actual_commits == [expected]


def test_non_contiguous_lines():
    UUID1 = '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775'
    commit1 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 1})
    commit2 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 3})
    commit3 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 5})
    owners = whodunit.CoverageOwners(".")
    owners.commits = [commit1, commit2, commit3]
    expected_commits = copy.copy(owners.commits)

    actual_commits = owners.sort()
    assert actual_commits == expected_commits


def test_contiguous_lines():
    UUID1 = '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775'
    commit1 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 1})
    commit2 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 2})
    commit3 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 5})
    owners = whodunit.CoverageOwners(".")
    owners.commits = [commit1, commit2, commit3]

    actual_commits = owners.sort()
    assert len(actual_commits) == 2
    assert actual_commits[0].lines == '1-2'
    assert actual_commits[0].uuid == UUID1
    assert actual_commits[1].uuid == UUID1
    assert actual_commits[1].lines == '5'


def test_contiguous_lines_different_commit():
    UUID1 = '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775'
    UUID2 = '65491efbd9ea0843c00cb50ff4c89211862924de'
    commit1 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 1})
    commit2 = create_commit({'uuid': UUID2, 'lines': 1, 'line_number': 2})
    commit3 = create_commit({'uuid': UUID2, 'lines': 1, 'line_number': 5})
    owners = whodunit.CoverageOwners(".")
    owners.commits = [commit1, commit2, commit3]
    expected_commits = copy.copy(owners.commits)

    actual_commits = owners.sort()
    assert len(actual_commits) == 3
    assert actual_commits == expected_commits


def test_last_commit_part_of_contiguous_region():
    UUID1 = '6e3b3aec8a73da4129e83554ad5ac2f43d4ec775'
    commit1 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 1})
    commit2 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 2})
    commit3 = create_commit({'uuid': UUID1, 'lines': 1, 'line_number': 3})
    owners = whodunit.CoverageOwners(".")
    owners.commits = [commit1, commit2, commit3]

    actual_commits = owners.sort()
    assert len(actual_commits) == 1
    assert actual_commits[0].lines == '1-3'


def test_is_git_file():
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.returncode = 0
        assert whodunit.Owners.is_git_file('.', 'foo.py')
    expected = [mock.call(['git', 'ls-files', '--error-unmatch', 'foo.py'],
                          stderr=-1, stdout=-1)]
    assert popen.call_count == 1
    popen.assert_has_calls(expected)


def test_is_not_git_file():
    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.returncode = 1
        assert not whodunit.Owners.is_git_file('.', 'foo.py')
    expected = [mock.call(['git', 'ls-files', '--error-unmatch', 'foo.py'],
                          stderr=-1, stdout=-1)]
    assert popen.call_count == 1
    popen.assert_has_calls(expected)


def test_collecting_modules(monkeypatch):
    owners = whodunit.Owners('/some/path')

    with mock.patch('os.walk') as walker:
        walker.return_value = [('/some/path', (), ('foo.py', 'bar.py')), ]

        def is_git(cls, path, name):
            return True
        monkeypatch.setattr(whodunit.Owners, 'is_git_file', is_git)

        modules = owners.collect_modules()
        expected = [('/some/path/foo.py', []), ('/some/path/bar.py', [])]
        assert list(modules) == expected


def tests_filtering_modules(monkeypatch):
    owners = whodunit.Owners('/some/path', filter="*.py")

    with mock.patch('os.walk') as walker:
        walker.return_value = [('/some/path', (), ('a.py', 'skip', 'b.py')), ]

        def is_git(cls, path, name):
            return True
        monkeypatch.setattr(whodunit.Owners, 'is_git_file', is_git)

        modules = owners.collect_modules()
        expected = [('/some/path/a.py', []), ('/some/path/b.py', [])]
        assert list(modules) == expected


def test_collecting_blame_info(monkeypatch, capsys):
    matches = [('path/a.py', [(1, 1)]),
               ('b.py', [(5, 5), (10, 10)])]

    def dummy_chdir(path):
        pass
    monkeypatch.setattr(os, 'chdir', dummy_chdir)

    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.side_effect = [('blame1', ''),
                                                      ('blame5+10', '')]
        blame_info = whodunit.Owners.collect_blame_info(matches)

        assert list(blame_info) == ['blame1', 'blame5+10']
    assert popen.call_count == 2
    expected = [
        mock.call(['git', 'blame', '--line-porcelain',
                   '-L 1,1', 'a.py'],
                  stderr=-1, stdout=-1),
        mock.call().communicate(),
        mock.call(['git', 'blame', '--line-porcelain',
                   '-L 5,5', '-L 10,10', 'b.py'],
                  stderr=-1, stdout=-1),
        mock.call().communicate()
    ]
    popen.assert_has_calls(expected)
    out, err = capsys.readouterr()
    expected = """

path/

a.py 

./

b.py """
    assert out == expected


def test_fail_collecting_blame_info(monkeypatch, capsys):
    matches = [('path/a.py', [(1, 1)]), ]

    def dummy_chdir(path):
        pass
    monkeypatch.setattr(os, 'chdir', dummy_chdir)

    with mock.patch.object(subprocess, 'Popen', create=True) as popen:
        popen.return_value.communicate.return_value = ('', 'blame fail')
        blame_info = whodunit.Owners.collect_blame_info(matches)

        assert list(blame_info) == []
    assert popen.call_count == 1
    expected = [
        mock.call(['git', 'blame', '--line-porcelain',
                   '-L 1,1', 'a.py'],
                  stderr=-1, stdout=-1),
        mock.call().communicate()
    ]
    popen.assert_has_calls(expected)
    out, err = capsys.readouterr()
    assert out == ("\n\npath/\n\na.py  <<<<<<<<<< Unable to collect 'git "
                   "blame' info: blame fail\n")


def test_collecting_coverage_modules(monkeypatch):
    """Collecting of files for coverage analysis.

    This demonstrates that the index.html file is skipped and a coverage
    file that has 100% coverage (simulated).
    """
    def is_a_file(filename):
        return True
    monkeypatch.setattr(os.path, 'isfile', is_a_file)

    def my_open(filename):
        return mock.MagicMock()
    monkeypatch.setattr('__builtin__.open', my_open)

    coverage_owners = whodunit.CoverageOwners('/some/repo')

    with mock.patch('os.listdir') as list_dir:
        list_dir.return_value = ['a_py.html', 'index.html',
                                 'path_b_py.html', 'covered100percent.html']
        with mock.patch.object(coverage_owners,
                               'determine_coverage') as get_cover:
            get_cover.side_effect = [('a.py', [(1, 1), ]),
                                     ('path/b.py', [(5, 5), (10, 10)]),
                                     ('', [])]
            modules = coverage_owners.collect_modules()
            expected = [('/some/repo/a.py', [(1, 1)]),
                        ('/some/repo/path/b.py', [(5, 5), (10, 10)])]
            assert list(modules) == expected


def test_fail_collecting_coverage_modules(monkeypatch):
    """Unable to find file corresponding to coverage file."""
    def is_a_file(filename):
        return False
    monkeypatch.setattr(os.path, 'isfile', is_a_file)

    def my_open(filename):
        return mock.MagicMock()
    monkeypatch.setattr('__builtin__.open', my_open)

    coverage_owners = whodunit.CoverageOwners('/some/repo')

    with mock.patch('os.listdir') as list_dir:
        list_dir.return_value = ['a_py.html', ]
        with mock.patch.object(coverage_owners,
                               'determine_coverage') as get_cover:
            get_cover.side_effect = [('a.py', [(1, 1), ]), ]
            with pytest.raises(whodunit.SourceNotFound) as snf:
                modules = coverage_owners.collect_modules()
                for module in modules:
                    pass
            expected = 'Source file a.py not found at /some/repo'
            assert snf.value.message == expected


def test_showing_details_of_date_sorted_commit(capsys):
    """Details are sorted by commit date, newest first."""
    commit1 = create_commit({'uuid': '11111111', 'committer_time': 1453922613})
    commit2 = create_commit({'uuid': '22222222', 'committer_time': 1454335722})
    commit3 = create_commit({'uuid': '33333333', 'committer_time': 1452193499})
    owners = whodunit.DateOwners(".", details=True)
    owners.commits = [commit1, commit2, commit3]
    owners.sort()
    owners.show_details(0)
    out, err = capsys.readouterr()
    expected = """    22222222    10 Joe Dirt                  2016-02-01
    11111111    10 Joe Dirt                  2016-01-27
    33333333    10 Joe Dirt                  2016-01-07
"""
    assert out == expected


def test_showing_details_of_size_sorted_commit(capsys):
    """Detailed data based on size per author.

    For one user, there are two commits, and will use the uuid for the newer
    commit. The total number of lines are aggregated for the authors.
    """
    commit1 = create_commit({'uuid': '11111111', 'lines': 20})
    commit2 = create_commit({'uuid': '1a1a1a1a', 'committer_time': 1455679427})
    commit3 = create_commit({'uuid': '22222222',
                             'author_mail': 'carl@coder.com',
                             'author': 'Carl Coder'})
    commit4 = create_commit({'uuid': '33333333', 'lines': 100,
                             'author_mail': 'zebra@zoo.com',
                             'author': 'Zebra Zoo'})
    owners = whodunit.SizeOwners(".", details=True)
    owners.commits = [commit1, commit2, commit3, commit4]
    owners.sort()
    owners.show_details(0)
    out, err = capsys.readouterr()
    expected = """    33333333   100 Zebra Zoo                 2016-02-01
    1a1a1a1a    30 Joe Dirt                  2016-02-16
    22222222    10 Carl Coder                2016-02-01
"""
    assert out == expected


def test_showing_details_of_coverage_commits(capsys):
    """Details for coverage are sorted (and grouped) by line number."""
    commit1 = create_commit({'uuid': '11111111', 'line_number': 5})
    commit2 = create_commit({'uuid': '22222222', 'line_number': 8})
    commit3 = create_commit({'uuid': '22222222', 'line_number': 9})
    commit4 = create_commit({'uuid': '33333333', 'line_number': 10})
    owners = whodunit.CoverageOwners(".")
    owners.commits = [commit1, commit2, commit3, commit4]
    owners.sort()
    owners.show_details(0)
    out, err = capsys.readouterr()
    expected = """    11111111           5 Joe Dirt                  2016-02-01
    22222222         8-9 Joe Dirt                  2016-02-01
    33333333          10 Joe Dirt                  2016-02-01
"""
    assert out == expected
