#!/usr/bin/env python3
"""
create-bodhi-update

Usage:
    create-bodhi-update [options] [--do] <release> <pkg>...
    create-bodhi-update [options] [--do] <release> --all

Options:
    --close-bugs

"""

from dataclasses import dataclass
from datetime import date as Date, timedelta as TimeDelta
import importlib
from pathlib import Path
from operator import itemgetter
import os
import re
import subprocess
import sys
import time

try:
    from docopt import docopt
except ImportError:
    sys.stderr.write('please install python3-docopt\n')
    sys.exit(1)


_bz = importlib.import_module('bugzilla-utils')
_git = importlib.import_module('git-utils')
_shell_utils = importlib.import_module('shell-utils')
display_output = _shell_utils.display_output
print_status_output = _shell_utils.print_status_output
run_cmd = _shell_utils.run_cmd
sanitize_pkg_names = _shell_utils.sanitize_pkg_names

_pkg_list = importlib.import_module('pkg-list')
parse_package_list = _pkg_list.parse_package_list


DIST_MAP = {
    'rawhide': 'fc34',
    'master' : 'fc34',

    'f33'    : 'fc33',
    'f32'    : 'fc32',
    'epel8'  : 'el8',
    'epel7'  : 'el7',
    # convenience aliases
    'el8'  : 'el8',
    'el7'  : 'el7',
}

def _extract_build_info(pkg_name, dist, koji_stdout):
    build_regex = re.compile(f'^({pkg_name}.+?\.{dist})\s+')
    for koji_line in koji_stdout.split('\n'):
        match = build_regex.search(koji_line)
        if not match:
            continue
        build = match.group(1)
        yield build

def query_koji(pkg_name, dist):
    today = Date.today()
    last_week = (today - TimeDelta(days=7))
    koji_cmd = [
        '/usr/bin/koji',
        'list-builds',
        f'--package={pkg_name}',
        '--reverse',
        '--state=COMPLETE',
        '--quiet',
        f'--after={last_week.isoformat()}',
    ]
    koji_proc = run_cmd(koji_cmd, wait=True)
    koji_stdout = koji_proc.stdout.read().decode('utf8')
    assert koji_proc.returncode == 0

    builds = tuple(_extract_build_info(pkg_name, dist, koji_stdout))
    if not builds:
        return None
    return builds[0]

def version_from_build(build):
    dist_pattern = f'\.({"|".join(DIST_MAP.values())})'
    version_pattern = f'\-(\d.+?)\-\d{dist_pattern}'
    match = re.search(version_pattern, build)
    new_version = match.group(1)
    return new_version

def submit_bodji_update(builds, bug_ids=(), autokarma=False, is_dry_run=False):
    new_version = version_from_build(builds[0])
    close_bugs = (len(bug_ids) > 0)
    filter_empty = lambda values: tuple(filter(bool, values))
    bodhi_cmd = filter_empty((
        '/usr/bin/bodhi',
        'updates',
        'new',
        '--request=testing',
        '--notes', f'update to {new_version}',
        '--type=enhancement',
        '--severity=low',
        '--autotime',
        '--autokarma',
        ('--close-bugs' if close_bugs else None),
        (f'--bugs={",".join(bug_ids)}' if bug_ids else None),
        ','.join(builds),
    ))
    if is_dry_run:
        shlex_join = subprocess.list2cmdline
        print(shlex_join(bodhi_cmd))
        return
    bodji_proc = run_cmd(bodhi_cmd, wait=True)
    bodhi_stdout = bodji_proc.stdout.read().decode('utf8')
    assert bodji_proc.returncode == 0
    print(bodhi_stdout)


def main():
    arguments = docopt(__doc__)
    branch_name = arguments['<release>']
    pkg_names = sanitize_pkg_names(arguments['<pkg>'])
    is_dry_run = not arguments['--do']
    close_bugs = arguments['--close-bugs']
    if not pkg_names:
        pkg_names = parse_package_list('CERTBOT-ALL-PACKAGES-AND-PLUGINS.txt')

    dist = DIST_MAP[branch_name]
    pkg_builds = {}
    for pkg_name in pkg_names:
        build = query_koji(pkg_name, dist)
        if build is None:
            print_status_output(pkg_name, is_error=True, msg='no build found')
        pkg_builds[pkg_name] = build
    builds = tuple(pkg_builds.values())

    bug_ids = ()
    if close_bugs:
        pkg_data = _bz.retrieve_release_notification_bugs(pkg_names)
        bug_ids = tuple(map(itemgetter(1), pkg_data.values()))
        if is_dry_run:
            for pkg_name, (bug_summary, bug_id) in pkg_data.items():
                print(f'{pkg_name}  #{bug_id}: {bug_summary}')

    submit_bodji_update(builds, bug_ids=bug_ids, autokarma=False, is_dry_run=is_dry_run)
    print_status_output('updates', is_error=False, msg=branch_name)

if __name__ == '__main__':
    main()

