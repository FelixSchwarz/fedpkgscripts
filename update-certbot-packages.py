#!/usr/bin/env python3
"""
update-certbot-packages.py

Usage:
    update-certbot-packages.py [options] [<pkg>...]

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

colorama_color = _colorama_utils.colorama_color
display_output = _shell_utils.display_output
print_status_output = _shell_utils.print_status_output
print_in_progress = _shell_utils.print_in_progress
parse_package_list = _pkg_list.parse_package_list
run_cmd = _shell_utils.run_cmd

THIS_DIR = Path(__file__).parent.resolve()


def extract_commands(stdout):
    if 'Already up to date' in stdout:
        return ()
    match = re.search('^(fedpkg new-sources .+?)$', stdout, re.MULTILINE)
    if not match:
        print('NO "fedpkg" command found!')
        return ()
    return (
        # fedpkg new-sources …
        match.group(1),
    )

def verify_gpg_signature(pkg_name, pkg_path):
    fedpkg_prep = run_cmd(['fedpkg', 'prep'], working_directory=pkg_path, wait=True, exit_on_error=False)
    if fedpkg_prep.returncode != 0:
        error = 'error while running "fedpkg prep"'
        print_status_output(pkg_name, is_error=True, msg=error)
        has_valid_signature = False
    else:
        fedpkg_stderr_str = fedpkg_prep.stderr.read().decode('utf8')
        has_valid_signature = 'gpgv: Good signature' in fedpkg_stderr_str
    return has_valid_signature


def main():
    arguments = docopt(__doc__)
    certbot_plugins = parse_package_list('CERTBOT-PLUGINS.txt')
    pkg_names = _shell_utils.sanitize_pkg_names(arguments['<pkg>'])

    verbose_dry_run = arguments['--verbose-dry-run']
    certbot_packages = (
        'python-acme',
        'certbot', *certbot_plugins)
    package_set = pkg_names or certbot_packages

    pkg_data = _bz.retrieve_release_notification_bugs(package_set)

    cmd_log = []
    bump_version = str(THIS_DIR / 'bump-rpm-version.sh')
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

        bump_cmd = [bump_version, pkg_name, bug_summary, bug_id]
        bump_proc = run_cmd(bump_cmd, working_directory=pkg_path, wait=True, exit_on_error=False)

        if bump_proc.returncode != 0:
            error = 'error while bumping version in spec file'
            print_status_output(pkg_name, is_error=True, msg=error)
            continue
        stdout_str = bump_proc.stdout.read().decode('utf8')
        pkg_cmds = extract_commands(stdout_str)
        if pkg_cmds:
            cmd_log.extend([
                f'cd {pkg_name}',
                *pkg_cmds,
                'git commit --amend --no-edit',
                'cd ..',
            ])

        has_valid_signature = verify_gpg_signature(pkg_name, pkg_path)
        if not has_valid_signature:
            print_status_output(pkg_name, is_error=True, msg='no valid signature')
            continue

        assert has_valid_signature
        cmd_str = pkg_cmds[0]
        assert cmd_str.startswith('fedpkg new-sources ')
        cmd_new_sources = shlex.split(cmd_str)
        sources_proc = run_cmd(cmd_new_sources, working_directory=pkg_path, wait=True, exit_on_error=False)
        if sources_proc.returncode != 0:
            print_status_output(pkg_name, is_error=True, msg='error while uploading new sources')
            continue
        run_cmd(['git', 'commit', '--amend', '--no-edit'], working_directory=pkg_path, wait=True, exit_on_error=True)

        print_status_output(pkg_name, is_error=False)

    if cmd_log:
        cmd_log.append('\n')
        with open('certbot-update-cmds.sh', 'w') as cmd_fp:
            cmd_fp.write('\n'.join(cmd_log))

if __name__ == '__main__':
    main()

