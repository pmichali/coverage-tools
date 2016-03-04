coverage-tools
==============

Tools for analyzing coverage for git based projects.

whodunit
--------

This helps identify the "owners" of lines in project files, with the intention
to assist in code coverage resolution (although can be used for other nefarious
purposes :).

USE CASE #1
In a git repo, you may want to know who can help fix coverage issues. Here,
whodunit can identify who is the author/committer for lines in a file or
a tree of files, starting at some directory. For example, from the top of a
project tree, you can enter:

<pre>
    python whodunit.py /opt/stack/neutron/neutron

    /opt/stack/neutron-lib/neutron_lib/

    constants.py (Andreas Scheuring, Doug Wiegley, Paul Michali, Li Ma, Abhishek Raut)
    __init__.py (Doug Wiegley)
    _i18n.py (Akihiro Motoki, Doug Wiegley)
    config.py (Doug Wiegley)
    exceptions.py (Doug Wiegley)
    version.py (Paul Michali)


    /opt/stack/neutron-lib/neutron_lib/api/

    converters.py (Paul Michali)
    __init__.py ()
    validators.py (Doug Wiegley, Paul Michali)
    ...
</pre>

This shows the directory, and then each file in the directory, with a list of
owners, as it recursively processes files. It will skip any files that are not
tracked by git.The default is to list the owners by most recent commit date.
More interesting, is to use the --detail option, where it shows more information
on each file:

<pre>
    validators.py (Doug Wiegley, Paul Michali)
        28523670   309 Doug Wiegley              2016-01-29
        7d9980f7   227 Paul Michali              2016-01-15
</pre>

Here you see the abbreviated commit ID, number of lines for that commit,
author, and date of the most recent commit (we're sorting by date). You
can add the --verbose option to see the author's email address, full date
and time  of the commit, the the committer's name and email address.

Alternately, you can sort the output by number of lines of code, per author
(and any committer(s) for that commit, in case the last commit was done
by someone else), by using "--sort size" argument, instead of the implied
default of "--sort date". This looks like this (with verbose on too):

<pre>
    dfa_db_models.py (Paul Michali, Nader Lahouti)
        4c637f50   306 Paul Michali <paul@example.com>                    2016-02-12 10:46:20 +0000 Sam Betts <sam@example.com>
        222f1afb    20 Nader Lahouti <nader@example.com>                  2015-10-06 09:51:26 -0700 Nader Lahouti <nadar@example.com>
</pre>

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


USE CASE #2

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

For example:
<pre>
    python whodunit.py -s cover /opt/stack/networking-cisco

    routerrole.py (Bob Melander)
        a238bf6b          54 Bob Melander              2015-10-13
        a238bf6b       61-64 Bob Melander              2015-10-13
</pre>

Here, the same commit, author, and date information information is shown
(and committer, if --verbose used), but the number after the commit ID is
the line number, or line range in the file.

You can use the -h option to see what the arguments are for this script.


my_coverage
-----------

This allows you to assess the coverage of changes you have in a repo. It
is intended for use, when preparing to push code up for review upstream.

As a prerequisite to using this script, run coverage in the repo, to
produce coverage report files in a 'cover' directory at the root of the
repo's tree. This coverage should be done on the code that will be
upstreamed (either what is in the working directory, or what has been
committed to the local repo).

Assuming you have a repo with uncommitted changes, you can run the command
as follows:

<pre>
    python my_coverage.py /opt/stack/networking-cisco
</pre>

The argument must be the root of a git repo that has coverage data in a
'cover' subdirectory.

By default, this will create diffs comparing the working directory, to the
latest commit (HEAD), with (up to) three lines of context. That output will
be checked against coverage data and a report produced. Here's what the
output looks like:

<pre>
    devstack/csr1kv/cisco_neutron (No coverage data)

    networking_cisco/apps/saf/agent/dfa_agent.py (No added/changed lines)

    networking_cisco/apps/saf/server/dfa_server.py (run=1, mis=1, par=0, ign=0) 47%
       32 run  import time
       33      
       34      
       35 run +from networking_cisco._i18n import _LE, _LI, _LW
       36 run  from oslo_serialization import jsonutils
       37      
       38      
    
      382              # it is created by openstack.
      383 run          part_name = self.cfg.dcnm.default_partition_name
      384 par          if len(':'.join((proj_name, part_name))) > 32:
      385 mis +            LOG.error(_LE('Invalid project name length: %s. The length of '
      386                                'org:part name is greater than 32'),
      387                            len(':'.join((proj_name, part_name))))
      388 mis              return
</pre>

Each file from the diff will be reported. If the file was not processed
byt the coverage test, or there were no added or changed lines in the
diff for the file, this will be reported, as shown in the first two files.

For files with coverage data and added/changes lines, the output will
look like the third file. Each line number from the diff is shown, with
the coverage status, which can be:

- 'run'  The line was invoked as part of coverage run
- 'mis'  The line was not invoked during coverage
- 'par'  The line was partially covered
- '   '  The line was not considered for coverage (e.g. blank, non-executable)

Next, if the line was added/changed, a '+' is shown. If it was a context line
for the diff region, a ' ' is shown. Deleted lines are not shown. After that,
the source code is show.

Next to the filename is summary information, ONLY for lines that were added
or changed. In the example, there was one line run and one missing in the
change set (lines with a plus sign). At the end, we can see the overall
coverage report for the FILE - 47% in this example.

There are a few knobs that you can use with this script. First, you can change
the number of context lines shown by using the --context argument. The default
is three, and can be zero or more. Note: if a diff region is at the start or
end of a file, there may be fewer or no context lines.

Second, you can select which commits are used for the diff calculation, by
specifying the --which argument. The default is 'working', which will do a
diff between the working directory and latest commit (HEAD). Instead, you can
provide 'committed', which will compare the current commit against the
previous commit (HEAD^..HEAD). Otherwise, you can provide the commit versions
to use for the diff, just make sure that the most recent corresponds to the
coverage report. For example, you can do:

<pre>
    cd /opt/stack/neutron
    python my_coverage.py --context 5 --which HEAD~5..HEAD~ .
</pre>

This runs the tool on a neutron repo, shows more context lines, and will
do a diff between HEAD~5 and HEAD~ commits.

You can use the -h option to see what the arguments are for this script.
