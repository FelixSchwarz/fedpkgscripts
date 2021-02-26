#!/usr/bin/env python3
"""
push-changes.py

Usage:
    push-changes.py [options] <pkg>...
    push-changes.py [options] --plugins

Options:
  --branches=<branches>     which branches to push [default: master]
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
_git = importlib.import_module('git-utils')
_pkg_list = importlib.import_module('pkg-list')
_shell_utils = importlib.import_module('shell-utils')

print_status_output = _shell_utils.print_status_output
print_in_progress = _shell_utils.print_in_progress
sanitize_pkg_names = _shell_utils.sanitize_pkg_names
parse_package_list = _pkg_list.parse_package_list

THIS_DIR = Path(__file__).parent.resolve()

def main():
    arguments = docopt(__doc__)
    pkg_names = sanitize_pkg_names(arguments['<pkg>'])
    branches_str = arguments['--branches']
    branches = re.split('\s*,\s*', branches_str)
    if not pkg_names:
        pkg_names = parse_package_list('CERTBOT-PLUGINS.txt')

    for pkg_name in pkg_names:
        print_in_progress(pkg_name)
        pkg_path = (THIS_DIR / '..' / pkg_name).resolve()

        if _git.has_uncommitted_changes(pkg_path):
            error_msg = 'uncommitted changes, skipping package'
            print_status_output(pkg_name, is_error=True, msg=error_msg)
            continue
        for branch in branches:
            _git.push_branch(branch, pkg_path)

        branch_str = ', '.join(branches)
        print_status_output(pkg_name, is_error=False, msg=branch_str)


if __name__ == '__main__':
    main()

