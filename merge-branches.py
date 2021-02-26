#!/usr/bin/env python3
"""
merge-branches.py

Usage:
    merge-branches.py [options] <TARGET_BRANCHES> <pkg>...
    merge-branches.py [options] <TARGET_BRANCHES> --plugins

"""

import importlib
from pathlib import Path
import re
import sys

try:
    from docopt import docopt
except ImportError:
    sys.stderr.write('please install python3-docopt\n')
    sys.exit(1)


_pkg_list = importlib.import_module('pkg-list')
_git_utils = importlib.import_module('git-utils')
_git = _git_utils
_shell = importlib.import_module('shell-utils')
sanitize_pkg_names = _shell.sanitize_pkg_names

parse_package_list = _pkg_list.parse_package_list


SUPPORTED_BRANCHES = ('f34', 'f33', 'f32', 'epel7', 'epel8')

THIS_DIR = Path(__file__).parent.resolve()

def merge_branch(source_branch, target_branch, pkg_path):
    _git.switch_to_branch(target_branch, pkg_path)
    _shell.run_cmd(['/usr/bin/git', 'merge', source_branch, '--ff-only'], working_directory=pkg_path, wait=True)

def main():
    arguments = docopt(__doc__)
    source_branch = 'main'
    target_branches_str = arguments['<TARGET_BRANCHES>']
    pkg_names = sanitize_pkg_names(arguments['<pkg>'])
    if not pkg_names:
        pkg_names = parse_package_list('CERTBOT-PLUGINS.txt')

    target_branches = re.split('\s*,\s*', target_branches_str)
    unknown_branches = set(target_branches).difference(SUPPORTED_BRANCHES)
    if unknown_branches:
        bad_branches = ', '.join(unknown_branches)
        _shell.print_status_output(f'unknown branch {bad_branches}', is_error=True)
        sys.exit(1)

    for pkg_name in pkg_names:
        _shell.print_in_progress(pkg_name)
        pkg_path = (THIS_DIR / '..' / pkg_name).resolve()

        if _git.has_uncommitted_changes(pkg_path):
            msg = 'uncommitted changes, skipping merge'
            _shell.print_status_output(pkg_name, is_error=True, msg=msg)
            continue

        for target_branch in target_branches:
            merge_branch(source_branch, target_branch, pkg_path)
        _shell.print_status_output(pkg_name)


if __name__ == '__main__':
    main()

