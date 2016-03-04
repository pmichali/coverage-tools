import my_coverage as cover
    source_file, lines = cover.parse_diffs(diffs)
    expected = [cover.SourceLine(1), cover.SourceLine(2)]
    source_file, lines = cover.parse_diffs(diffs)
        cover.SourceLine(59), cover.SourceLine(60), cover.SourceLine(61),
        cover.SourceLine(62, False),
        cover.SourceLine(63), cover.SourceLine(64), cover.SourceLine(65)
    source_file, lines = cover.parse_diffs(diffs)
        cover.SourceLine(42), cover.SourceLine(43), cover.SourceLine(44),
        cover.SourceLine(45, False), cover.SourceLine(46, False),
        cover.SourceLine(47, False),
        cover.SourceLine(48)
    source_file, lines = cover.parse_diffs(diffs)
        cover.SourceLine(484), cover.SourceLine(485), cover.SourceLine(486),
        cover.SourceLine(487, False), cover.SourceLine(488, False),
        cover.SourceLine(489), cover.SourceLine(490), cover.SourceLine(491),
        cover.SourceLine(500), cover.SourceLine(501), cover.SourceLine(502),
        cover.SourceLine(503, False),
        cover.SourceLine(504), cover.SourceLine(505), cover.SourceLine(506),
        cover.SourceLine(526), cover.SourceLine(527), cover.SourceLine(528),
        cover.SourceLine(529, False)
    source_file, lines = cover.parse_diffs(diffs)
    assert lines == [cover.SourceLine(1, is_context=False)]
    source_file, lines = cover.parse_diffs(diffs)
    source_file, lines = cover.parse_diffs(diffs)
    assert lines == [cover.SourceLine(1, is_context=False)]
        diffs = cover.collect_diffs_for_files('/some/path', versions="HEAD",
        diffs = cover.collect_diffs_for_files('/some/path', versions="HEAD",
        with pytest.raises(cover.DiffCollectionFailed) as excinfo:
        diff_files = cover.collect_diff_files(fake_project, 'HEAD')
        diff_files = cover.collect_diff_files('/some/path', 'HEAD')
        with pytest.raises(cover.DiffCollectionFailed) as excinfo:
    module = cover.SourceModule(filename, lines=[])
    line = cover.SourceLine(10, is_context=False)
    module = cover.SourceModule('foo', [line])
    line = cover.SourceLine(10, is_context=False)
    module = cover.SourceModule('foo', [line])
    module = cover.SourceModule('foo.py', [])
    cover.check_coverage_status(coverage_info, module)
    non_executable_line = cover.SourceLine(63)
    partial_covered_line = cover.SourceLine(64, is_context=False)
    missing_line = cover.SourceLine(65, is_context=False)
    covered_line = cover.SourceLine(66, is_context=False)
    module = cover.SourceModule('foo.py', [non_executable_line,
                                           partial_covered_line,
                                           missing_line,
                                           covered_line])
    cover.check_coverage_status(coverage_info, module)
    module = cover.SourceModule('foo.py', [])
    cover.check_coverage_file(fake_cover_project, module)
    line = cover.SourceLine(2, is_context=False)
    module = cover.SourceModule('foo.py', [line])
        cover.check_coverage_file('.', module)
    module = cover.SourceModule('path/foo.py', [])
    module = cover.SourceModule('path/foo.py', [])
    lines = [cover.SourceLine(10, is_context=True),
             cover.SourceLine(12, is_context=True)]
    module = cover.SourceModule('deleted_lines_file', lines)
    line = cover.SourceLine(10, is_context=False, code='    x = 1')
    module = cover.SourceModule('path/foo.py', [line])
   10 run +     x = 1
    lines = [cover.SourceLine(10, is_context=False, code='x = 1'),
             cover.SourceLine(11, is_context=False, code='y = 2'),
             cover.SourceLine(20, is_context=False, code='z = 3'),
             cover.SourceLine(21, is_context=False, code='for i in [1, 2]')]
    module = cover.SourceModule('path/foo.py', lines)
   10 run + x = 1
   11 mis + y = 2
   20 par + z = 3
   21     + for i in [1, 2]
    parser = cover.setup_parser()
    args = cover.validate(parser, [fake_cover_project])
    args = cover.validate(parser, ['-w', 'working', fake_cover_project])
    args = cover.validate(parser, ['-w', 'committed', fake_cover_project])
    args = cover.validate(parser, ['-w', 'HEAD~5..HEAD~3', fake_cover_project])
    parser = cover.setup_parser()
    args = cover.validate(parser, ['-c', '10', fake_cover_project])
    parser = cover.setup_parser()
    assert cover.validate(parser, [fake_cover_project])
    parser = cover.setup_parser()
        cover.validate(parser, [fake_project])
    parser = cover.setup_parser()
        cover.validate(parser, ['bogus-dir'])