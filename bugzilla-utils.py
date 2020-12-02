
import csv
import importlib
from io import StringIO


_shell = importlib.import_module('shell-utils')

def retrieve_release_notification_bugs(pkg_names, *, verbose_dry_run=False):
    bz_stdout = query_bugzilla(pkg_names, verbose_dry_run=verbose_dry_run)
    return parse_bz_output(bz_stdout, pkg_names)

def query_bugzilla(pkg_names, *, verbose_dry_run=False):
    qs_str = '&'.join([
        'bug_status=NEW',
        'bug_status=ASSIGNED',
        'query_format=advanced',
        'emailreporter1=1',
        'emailtype1=substring',
        'email1=upstream-release-monitoring%40fedoraproject.org',
        *(map(lambda p: f'component={p}', pkg_names))
    ])
    query_url = f'https://bugzilla.redhat.com/buglist.cgi?{qs_str}'
    if verbose_dry_run:
        print(query_url)
    bugzilla_cmd = (
        '/usr/bin/bugzilla',
        'query',
        f'--from-url={query_url}',
        '--outputformat', '%{component}|%{summary}|%{id}'
    )
    bugzilla_proc = _shell.run_cmd(bugzilla_cmd, wait=True)
    bz_stdout = bugzilla_proc.stdout.read().decode('utf8')
    assert bugzilla_proc.returncode == 0
    return bz_stdout

def parse_bz_output(stdout_str, pkg_names):
    bz_fp = StringIO(stdout_str)

    pkg_data = {}
    for line in csv.reader(bz_fp, delimiter='|', quoting=csv.QUOTE_MINIMAL):
        pkg_name, bug_summary, bug_id = line
        if pkg_name not in pkg_names:
            continue
        pkg_data[pkg_name] = (bug_summary, bug_id)

    return pkg_data

