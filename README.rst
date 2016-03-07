whodunit
========

This helps identify the "owners" of lines in project files, with the intention
to assist in code coverage resolution (although can be used for other nefarious
purposes :).

Usage A: Ownership Detection
----------------------------

In a git repo, you may want to know who can help fix coverage issues. Here,
whodunit can identify who is the author/committer for lines in a file or
a tree of files, starting at some directory. For example, from the top of a
project tree, you can enter::

    whodunit /opt/stack/neutron/neutron

    /opt/stack/neutron-lib/neutron_lib/

    constants.py (Andy Able, Doug Delta, Felix Foxtrot, Leo Lion, Bob Baker)
    __init__.py (Doug Delta)
    _i18n.py (Charlie Coder, Doug Delta)
    config.py (Doug Delta)
    exceptions.py (Doug Delta)
    version.py (Felix Foxtrot)


    /opt/stack/neutron-lib/neutron_lib/api/

    converters.py (Felix Foxtrot)
    __init__.py ()
    validators.py (Doug Delta, Felix Foxtrot)
    ...

This shows the directory, and then each file in the directory, with a list of
owners, as it recursively processes files. It will skip any files that are not
tracked by git.The default is to list the owners by most recent commit date.
More interesting, is to use the --detail option, where it shows more information
on each file::

    validators.py (Doug Delta, Felix Foxtrot)
        28523670   309 Doug Delta                 2016-01-29
        7d9980f7   227 Felix Foxtrot              2016-01-15

Here you see the abbreviated commit ID, number of lines for that commit,
author, and date of the most recent commit (we're sorting by date). You
can add the --verbose option to see the author's email address, full date
and time  of the commit, the the committer's name and email address.

Alternately, you can sort the output by number of lines of code, per author
(and any committer(s) for that commit, in case the last commit was done
by someone else), by using "--sort size" argument, instead of the implied
default of "--sort date". This looks like this (with verbose on too)::

    dfa_db_models.py (Felix Foxtrot, Nader Lahouti)
        4c637f50   306 Felix Foxtrot <fox@example.com>                    2016-02-12 10:46:20 +0000 Sam Source <sam@example.com>
        222f1afb    20 Ned Nerf <ned@example.com>                         2015-10-06 09:51:26 -0700 Ned Nerf <ned@example.com>

With the summary list of authors shown next to the file name, they are
in the order based on the sort. For sorting by size, the author with
the most lines is shown first. For sorting by date, the author with
the most recent commit is shown first. Duplicates are removed, in that
case, so you may have fewer names in the summary, if a person has
several commits.

You can limit the amount of output, by using the --max option,
which, by default is set to zero to show all output. With "--sort date",
it'll show the N most recent commits, by size, it'll show the N largest
author lines per file. This can liit things to the most recent commits
or most significant authors.

You can use the --filter option to restrict the files that are evaluated.
This is a regular expression like value, where '*' matches '.' as well,
so hidden files would be included, with the default value of '*'.

Instead of providing a directory to start from, you can provide an
individual file (tracked by git), and it will produce a report for that
file.


Usage A: Coverage Ownership
---------------------------

If you have run a coverage test in the repo, and have a cover directory
with coverage reports on the repo files, you can use whodunit to provide
ownership for lines in modules that are missing coverage or have partial
coverage.

To do this, you specify the root directory for the repo, and provide
the "--sort cover" argument. This will automatically select the --detail
option. You can choose to use the --verbose option for author email,
full date/time, and committer name and email output in the report.

You cannot specify the --max option to limit the output (which doesn't
make sense as you want to see all the lines that do not have coverage.
Likewise, the --filter and --details options are not allowed either.
The filter is forced to "*", and details are implied in the output.

For example::

    whodunit -s cover /opt/stack/networking-cisco

    routerrole.py (Bob Betatester)
        a238bf6b          54 Bob Betatester            2015-10-13
        a238bf6b       61-64 Bob Betatester            2015-10-13

Here, the same commit, author, and date information information is shown
(and committer, if --verbose used), but the number after the commit ID is
the line number, or line range in the file.

You can use the -h option to see what the arguments are for this script.
