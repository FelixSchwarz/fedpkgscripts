#!/usr/bin/env python3
"""
check-for-uncommitted-changes.py

Usage:
    check-for-uncommitted-changes.py [--with-version] [<pkg>...]
"""

import importlib
from pathlib import Path

try:
    from docopt import docopt
except ImportError:
    sys.stderr.write('please install python3-docopt\n')
    sys.exit(1)

_git = importlib.import_module('git-utils')
_shell_utils = importlib.import_module('shell-utils')
display_output = _shell_utils.display_output
print_status_output = _shell_utils.print_status_output
sanitize_pkg_names = _shell_utils.sanitize_pkg_names
_pkg_list = importlib.import_module('pkg-list')
parse_package_list = _pkg_list.parse_package_list
_spec = importlib.import_module('spec-utils')

THIS_DIR = Path(__file__).parent.resolve()


def main():
    arguments = docopt(__doc__)
    show_version = arguments['--with-version']
    pkgs = sanitize_pkg_names(arguments['<pkg>']) or parse_package_list('CERTBOT-ALL-PACKAGES-AND-PLUGINS.txt')

    for pkg_name in pkgs:
        pkg_path = (THIS_DIR / '..' / pkg_name).resolve()

        if show_version:
            version = _spec.get_version_from_specfile(pkg_path, pkg_name)
            pkg_str = f'{pkg_name} ({version})'
        else:
            pkg_str = pkg_name

        if _git.has_uncommitted_changes(pkg_path):
            error_msg = 'uncommitted changes'
            print_status_output(pkg_str, is_warning=True, msg=error_msg)
        else:
            print_status_output(pkg_str)

if __name__ == '__main__':
    main()

