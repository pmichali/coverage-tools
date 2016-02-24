import collections
import pytest
import whodunit


line_one = """6e3b3aec8a73da4129e83554ad5ac2f43d4ec775 1813 1794 1794
author Carol Bouchard
author-mail <caboucha@cisco.com>
author-time 1453922613
author-tz -0500
committer Carol Bouchard
committer-mail <caboucha@cisco.com>
committer-time 1454335722
committer-tz -0500
summary Baremetal-Ironic development for Nexus ML2 drivers
previous 25088fc1e98735e811e6bac8c9930d44639130b9 networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
filename networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
\t\t\tfor switch_ip, attr2, attr3, attr4 in host_connections:
"""

line_two = """65491efbd9ea0843c00cb50ff4c89211862924de 790 1795
author Rich Curran
author-mail <rcurran@cisco.com>
author-time 1426193499
author-tz -0400
committer rcurran
committer-mail <rcurran@cisco.com>
committer-time 1427468897
committer-tz +0000
summary ML2 cisco_nexus MD: Sync of staging/junoplus
previous 495251e5c9d6a329ebe1631b1524a98b81ee76e6 networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
filename networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
                            physnet = self._nexus_switches.get((switch_ip, 'physnet'))
"""

line_three = """6e3b3aec8a73da4129e83554ad5ac2f43d4ec775 28 28 1
author Carol Bouchard
author-mail <caboucha@cisco.com>
author-time 1453922613
author-tz -0500
committer Carol Bouchard
committer-mail <caboucha@cisco.com>
committer-time 1454335722
committer-tz -0500
summary Baremetal-Ironic development for Nexus ML2 drivers
previous 25088fc1e98735e811e6bac8c9930d44639130b9 networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
filename networking_cisco/plugins/ml2/drivers/cisco/nexus/mech_cisco_nexus.py
\tfrom oslo_serialization import jsonutils
"""


def test_build_valid_record():
    record = whodunit.BlameRecord('some-uuid')
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
    record = whodunit.BlameRecord('some-uuid')
    record.store_attribute('committer-time', '1391791021')
    record.store_attribute('committer-tz', '-0500')
    assert record.date == '2014-02-07 11:37:01 -0500'


def test_ignoring_blame_info():
    record = whodunit.BlameRecord('some-uuid')
    record.store_attribute('summary', 'do not store summary')
    assert not hasattr(record, 'summary')
    record.store_attribute('filename', 'do not store file info')
    assert not hasattr(record, 'filename')
    record.store_attribute('previous', 'do not store previous commit info')
    assert not hasattr(record, 'previous')


def test_fail_record_missing_author():
    record = whodunit.BlameRecord('some-uuid')
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
    record = whodunit.BlameRecord('some-uuid')
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
    record = whodunit.BlameRecord('some-uuid')
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

    record = whodunit.BlameRecord('some-uuid')
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
    record = whodunit.BlameRecord('some-uuid')
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

    record = whodunit.BlameRecord('some-uuid')
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
    record = whodunit.BlameRecord('some-uuid')
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
    record = whodunit.BlameRecord('some-uuid')
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


def test_fail_extract_blame_info_for_two_commits():
    blame_output = line_one + line_two
    commits = whodunit.parse_info_records(blame_output)
    assert len(commits) == 2
    uuid1 = "6e3b3aec8a73da4129e83554ad5ac2f43d4ec775"
    assert uuid1 in commits
    record = commits[uuid1]
    assert record.uuid == "6e3b3aec8a73da4129e83554ad5ac2f43d4ec775"
    assert record.line_count == 1
    assert record.author == "Carol Bouchard"
    assert record.date == "2016-02-01 09:08:42 -0500"
    assert record.author_mail == "<caboucha@cisco.com>"
    uuid2 = "65491efbd9ea0843c00cb50ff4c89211862924de"
    assert uuid2 in commits
    record = commits[uuid2]
    assert record.uuid == "65491efbd9ea0843c00cb50ff4c89211862924de"
    assert record.line_count == 1
    assert record.author == "Rich Curran"
    assert record.date == "2015-03-27 15:08:17 +0000"
    assert record.author_mail == "<rcurran@cisco.com>"


def test_two_records_same_commit():
    blame_output = line_one + line_three
    commits = whodunit.parse_info_records(blame_output)
    assert len(commits) == 1
    uuid1 = "6e3b3aec8a73da4129e83554ad5ac2f43d4ec775"
    assert uuid1 in commits
    record = commits[uuid1]
    assert record.uuid == "6e3b3aec8a73da4129e83554ad5ac2f43d4ec775"
    assert record.line_count == 2
    assert record.author == "Carol Bouchard"
    assert record.date == "2016-02-01 09:08:42 -0500"
    assert record.author_mail == "<caboucha@cisco.com>"


def create_commit(info):
    commit = whodunit.BlameRecord(info['uuid'])
    commit.line_count = info['lines'] if 'lines' in info else 10
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
    commit = whodunit.merge_user_commits([commit1])
    assert commit == commit1


def test_merge_two_with_second_newer():
    commit1 = create_commit({'uuid': 'uuid-1', 'committer_time': 1453922613})
    commit2 = create_commit({'uuid': 'uuid-2', 'committer_time': 1456193499})
    commit = whodunit.merge_user_commits([commit1, commit2])
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
    commits = {'uuid-1': commit1, 'uuid-2': commit2, 'uuid-3': commit3}

    sorted_commits = whodunit.sort_by_size(commits)

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
    commits = {'uuid1': commit1, 'uuid-2': commit2, 'uuid-3': commit3}
    sorted_commits = whodunit.sort_by_date(commits)
    assert len(sorted_commits) == 3
    assert sorted_commits == [commit2, commit1, commit3]
