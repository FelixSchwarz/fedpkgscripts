#!/usr/bin/env python3
"""
bump-rpm-version.py

Usage:
    bump-rpm-version.py [--no-upload] <package> <version>
    bump-rpm-version.py [--no-upload] <package> <bug-summary> <bug-id>
"""

import importlib
from pathlib import Path
import re

from docopt import docopt

_git = importlib.import_module('git-utils')
_shell_utils = importlib.import_module('shell-utils')
print_status_output = _shell_utils.print_status_output
run_cmd = _shell_utils.run_cmd
_spec = importlib.import_module('spec-utils')


def _bump_spec(pkg_path, pkg_name, new_version, message):
    bumpspec_cmd = [
        '/usr/bin/rpmdev-bumpspec',
        f'--new={new_version}',
        f'--comment={message}',
        '--legacy-datestamp',
        f'{pkg_name}.spec'
    ]
    bumpspec_proc = run_cmd(bumpspec_cmd, working_directory=pkg_path, wait=True, exit_on_error=False)
    if bumpspec_proc.returncode != 0:
        error = 'error while retrieving previous version from spec file'
        _shell_utils.print_status_output(pkg_name, is_error=True, msg=error)


def _download_new_sources(pkg_path, pkg_name):
    spectool_cmd = ['/usr/bin/spectool', '--get-files', f'{pkg_name}.spec']
    spectool_proc = run_cmd(spectool_cmd, working_directory=pkg_path, wait=True, exit_on_error=False)
    if spectool_proc.returncode != 0:
        error = 'error while downloading new sources'
        _shell_utils.print_status_output(pkg_name, is_error=True, msg=error)
        return ()

    stdout_str = spectool_proc.stdout.read().decode('utf8').strip()
    filenames = set()
    fn_patterns = (
        #r'^Downloading: .*/(.+\-.*.tar.gz.*)$',
        r'^Downloaded: (.+\-.*.tar.gz.*)$',
    )
    for line in re.split('\n', stdout_str):
        for pattern in fn_patterns:
            match = re.search(pattern, line)
            if match:
                break
        else:
            #print('skipping %s' % line)
            continue
        filename = match.group(1)
        filenames.add(filename)
    return tuple(filenames)


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
    pkg_name = arguments['<package>']
    new_version = arguments['<version>']
    bug_summary = arguments['<bug-summary>']
    bug_id = arguments['<bug-id>']
    upload_new_sources = not arguments['--no-upload']

    if bug_summary:
        match = re.search(f'{pkg_name}\-(.+) is available', bug_summary)
        new_version = match.group(1)

    pkg_path = Path('.')

    old_version = _spec.get_version_from_specfile(pkg_path, pkg_name)
    if old_version == new_version:
        print(f'Already up to date ({old_version})')
        return
    print(f'{old_version} -> {new_version}')

    message = f'Update to {new_version}'
    if bug_id:
        message += f' (#{bug_id})'
    _bump_spec(pkg_path, pkg_name, new_version, message)
    _git.add(pkg_path, f'{pkg_name}.spec')

    new_sources = _download_new_sources(pkg_path, pkg_name)
    #print(new_sources)
    has_valid_signature = verify_gpg_signature(pkg_name, pkg_path)
    if not has_valid_signature:
        print_status_output(pkg_name, is_error=True, msg='no valid signature')
        return
    
    if new_sources:
        cmd_new_sources = ('fedpkg', 'new-sources', *new_sources)
        if upload_new_sources:
            sources_proc = run_cmd(cmd_new_sources, working_directory=pkg_path, wait=True, exit_on_error=False)
            if sources_proc.returncode != 0:
                print_status_output(pkg_name, is_error=True, msg='error while uploading new sources')
                return
        else:
            print(' '.join(cmd_new_sources))

    _git.commit(pkg_path, message)

if __name__ == '__main__':
    main()
