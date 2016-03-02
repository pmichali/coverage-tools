from my_coverage import check_coverage_status
def test_extract_single_added_line():
    assert lines[0].code == "INSTANCE_PC = 'testpcvm'"
    assert lines[1].code == "INSTANCE_DUAL = 'testdualvm'"
    assert lines[2].code == ""
    assert lines[3].code == "NEXUS_BAREMETAL_PORT_1 = 'Ethernet 1/10'"
    assert lines[4].code == "NEXUS_PORT_1 = 'ethernet:1/10'"
    assert lines[5].code == "NEXUS_PORT_2 = 'ethernet:1/20'"
    assert lines[6].code == "NEXUS_DUAL1 = 'ethernet:1/3'"
def test_update_status_line():
    line = SourceLine(10, is_context=False)
    module = SourceModule('foo', [line])
    module.update_line_status(10, 'pln')
    assert line.status == '   '
    module.update_line_status(10, 'stm run')
    assert line.status == 'run'
    module.update_line_status(10, 'stm mis')
    assert line.status == 'mis'
    module.update_line_status(10, 'stm par')
    assert line.status == 'par'


def test_fail_update_status_no_matching_line():
    line = SourceLine(10, is_context=False)
    module = SourceModule('foo', [line])
    module.update_line_status(12, 'stm run')
    assert line.status == '???'


    module = SourceModule('foo.py', [])
    check_coverage_status(coverage_info, module)
    assert module.lines == []
def test_coverage_updating():
<p id="n63" class="pln"><a href="#n63">63</a></p>
<p id="n64" class="stm par run hide_run"><a href="#n64">64</a></p>
<p id="n65" class="stm mis"><a href="#n65">65</a></p>
<p id="n66" class="stm run hide_run"><a href="#n66">66</a></p>
    non_executable_line = SourceLine(63)
    partial_covered_line = SourceLine(64, is_context=False)
    missing_line = SourceLine(65, is_context=False)
    covered_line = SourceLine(66, is_context=False)
    module = SourceModule('foo.py', [non_executable_line, partial_covered_line,
                                     missing_line, covered_line])
    check_coverage_status(coverage_info, module)
    assert non_executable_line.status == '   '
    assert partial_covered_line.status == 'par'
    assert missing_line.status == 'mis'
    assert covered_line.status == 'run'