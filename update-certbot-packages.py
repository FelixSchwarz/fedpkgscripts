#!/usr/bin/env python3
"""
update-certbot-packages.py

Usage:
    update-certbot-packages.py [options] <pkg>...
    update-certbot-packages.py [options] --all

Options:
  --verbose-dry-run        query bugzilla only
"""

import importlib
from pathlib import Path
import re
import shlex
import sys
from urllib.parse import quote as url_quote

try:
    from docopt import docopt
except ImportError:
    sys.stderr.write('please install python3-docopt\n')
    sys.exit(1)

_bz = importlib.import_module('bugzilla-utils')
_colorama_utils = importlib.import_module('colorama-utils')
_git = importlib.import_module('git-utils')
_pkg_list = importlib.import_module('pkg-list')
_shell_utils = importlib.import_module('shell-utils')
_fed_utils = importlib.import_module('fedora-utils')

colorama_color = _colorama_utils.colorama_color
display_output = _shell_utils.display_output
print_status_output = _shell_utils.print_status_output
print_in_progress = _shell_utils.print_in_progress
parse_package_list = _pkg_list.parse_package_list
run_cmd = _shell_utils.run_cmd

THIS_DIR = Path(__file__).parent.resolve()


def main():
    arguments = docopt(__doc__)
    package_set = _shell_utils.sanitize_pkg_names(arguments['<pkg>'])
    verbose_dry_run = arguments['--verbose-dry-run']

    if not package_set:
        package_set = parse_package_list('CERTBOT-ALL-PACKAGES-AND-PLUGINS.txt')

    if not _fed_utils.has_kerberos_ticket():
        print_status_output('no valid kerberos ticket', is_warning=True)
        return

    pkg_data = _bz.retrieve_release_notification_bugs(package_set)

    for pkg_name in package_set:
        if pkg_name not in pkg_data:
            print_status_output(pkg_name, is_warning=True, msg='no bugzilla issue')
            continue
        (bug_summary, bug_id) = pkg_data[pkg_name]
        progress_msg = f'#{bug_id} -- {bug_summary}' if verbose_dry_run else ''
        print_in_progress(pkg_name, msg=progress_msg)
        assert 'is available' in bug_summary
        pkg_path = (THIS_DIR / '..' / pkg_name).resolve()

        if _git.has_uncommitted_changes(pkg_path):
            error_msg = 'uncommitted changes, skipping package'
            print_status_output(pkg_name, is_error=True, msg=error_msg)
            continue
        elif verbose_dry_run:
            # ensure next package name is printed on a new line
            # "print_in_progress()" prints without newline
            print('\n', end='')
            continue
        _git.switch_to_branch('master', pkg_path)
        _git.pull('origin', pkg_path, ff_only=True)

        bump_version = str(THIS_DIR / 'bump-rpm-version.py')
        bump_cmd = [bump_version, pkg_name, bug_summary, bug_id]
        bump_proc = run_cmd(bump_cmd, working_directory=pkg_path, wait=True, exit_on_error=False)
        if bump_proc.returncode != 0:
            error = 'error while bumping version in spec file'
            print_status_output(pkg_name, is_error=True, msg=error)
            continue
        bump_str = bump_proc.stdout.read().decode('utf8').strip()

        print_status_output(pkg_name, msg=bump_str, is_error=False)

if __name__ == '__main__':
    main()

