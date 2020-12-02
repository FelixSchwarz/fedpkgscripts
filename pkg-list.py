
import re


__all__ = [
    'parse_package_list',
]

def parse_package_list(filename):
    pkg_names = []
    with open(filename, 'r') as fp:
        for line in fp.readlines():
            match = re.search('^\s*([a-zA-Z\-_0-9]+)$', line)
            if match:
                pkg_names.append(match.group(1))
    return pkg_names


