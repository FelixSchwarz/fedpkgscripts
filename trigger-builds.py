#!/usr/bin/env python3
"""
trigger-builds

Usage:
   trigger-builds (--scratch|--mock|--build|--copr=<COPR>) [options] <pkg>...
   trigger-builds (--scratch|--mock|--build|--copr=<COPR>) [options] --plugins

Options:
   --branch=<branch>            which branch to build [default: master]

"""

from dataclasses import dataclass
import importlib
from pathlib import Path
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


_git = importlib.import_module('git-utils')
_shell_utils = importlib.import_module('shell-utils')
display_output = _shell_utils.display_output
print_status_output = _shell_utils.print_status_output
run_cmd = _shell_utils.run_cmd
sanitize_pkg_names = _shell_utils.sanitize_pkg_names

_pkg_list = importlib.import_module('pkg-list')
parse_package_list = _pkg_list.parse_package_list


def create_srpm(pkg_path):
    cmd = ['/usr/bin/fedpkg', 'srpm']
    proc = run_cmd(cmd, working_directory=pkg_path)
    match = re.search(b'Wrote:\s*(.+?)\n', proc.stdout.read())
    if not match:
        display_output(proc.stdout.read(), proc.stderr.read())
    byte_path = match.group(1)
    # Path() does not accept bytes
    path_src_rpm = Path(byte_path.decode('UTF8'))
    return path_src_rpm


@dataclass
class BuildProcess:
    pkg_name: str
    proc    : subprocess.Popen
    type_   : str
    stdout  : bytes = b''
    stderr  : bytes = b''
    _rc     : int   = None
    url     : str   = None
    task_id : int   = None

    def is_build_done(self, consume_output=True):
        return self.is_process_done(consume_output=consume_output)

    def did_fail(self):
        return (self.is_build_done() and not self.was_successful())

    def was_successful(self):
        if not self.is_build_done():
            return None
        # TODO: Check output
        return (self.rc == 0)

    def is_process_done(self, consume_output=True):
        was_running = (self._rc is None)
        is_running = (self.rc is None)
        is_done = not is_running
        if was_running and is_done and consume_output:
            stdout, stderr = self.proc.communicate()
            self.stdout += stdout
            self.stderr += stderr
        return is_done

    @property
    def rc(self):
        if self._rc is None:
            self.proc.poll()
            self._rc = self.proc.returncode
        return self._rc


def trigger_koji_build(pkg_path, *, scratch):
    pkg_name = pkg_path.name
    path_src_rpm = None
    if scratch:
        cmd = ['/usr/bin/fedpkg', 'scratch-build']
        if _git.has_unpushed_changes(pkg_path):
            path_src_rpm = create_srpm(pkg_path)
            cmd += ['--srpm', str(path_src_rpm)]
    else:
        cmd = ['/usr/bin/fedpkg', 'build']
    fedpkg_proc = run_cmd(cmd, working_directory=pkg_path)
    build = BuildProcess(pkg_name=pkg_name, proc=fedpkg_proc, type_='koji')
    task_info_regex = re.compile(b'Task info: (https://.+?\=(\d+))\n')
    _extract_urls_from_build_output(build, task_info_regex)
    if path_src_rpm:
        path_src_rpm.unlink()
    return build


def _extract_urls_from_build_output(build, regex, *, multiline_regex=False):
    while True:
        build_output = build.proc.stdout.readline()
        if build_output:
            build.stdout += build_output
            match = regex.search(build.stdout if multiline_regex else build_output)
            if match:
                build.url = match.group(1).decode('utf8')
                build.task_id = match.group(2).decode('utf8')
                break
        elif build.is_process_done():
            break

def trigger_copr_build(pkg_path, copr_repo):
    pkg_name = pkg_path.name
    path_src_rpm = create_srpm(pkg_path)
    cmd = ['/usr/bin/copr-cli', 'build', copr_repo, str(path_src_rpm)]
    copr_proc = run_cmd(cmd, working_directory=pkg_path)
    build = BuildProcess(pkg_name=pkg_name, proc=copr_proc, type_='copr')

    pattern = (
        b'Build was added to ' + copr_repo.encode('ascii') + b':' + \
        b'\s*(https://.+?/build/(\d+))\s*\n'
    )
    build_url_regex = re.compile(pattern)
    _extract_urls_from_build_output(build, build_url_regex, multiline_regex=True)
    path_src_rpm.unlink()
    return build


def trigger_mock_build(pkg_path, *, wait=False):
    pkg_name = pkg_path.name

    cmd = ['/usr/bin/fedpkg', 'mockbuild']
    mock_proc = run_cmd(cmd, working_directory=pkg_path)
    build = BuildProcess(pkg_name=pkg_name, proc=mock_proc, type_='mock')
    if wait:
        build.proc.wait()
    return build

def _handle_build_completion(build, builds_in_progress):
    if not build.is_build_done():
        return
    builds_in_progress.remove(build)

    # LATER: new package version would be nice
    print_status_output(build.pkg_name, is_error=(not build.was_successful()))
    if build.did_fail():
        display_output(build.stdout, build.stderr, header_str=build.pkg_name)

def _wait_for_build_completion(builds_in_progress):
    while builds_in_progress:
        for build in tuple(builds_in_progress):
            _handle_build_completion(build, builds_in_progress)
        time.sleep(1)


def main():
    arguments = docopt(__doc__)
    branch_name = arguments['--branch'] or 'master'
    copr_repo = arguments['--copr']

    is_koji_build = (arguments['--scratch'] or arguments['--build'])
    pkg_names = sanitize_pkg_names(arguments['<pkg>'])
    if not pkg_names:
        pkg_names = parse_package_list('CERTBOT-PLUGINS.txt')
    builds_in_progress = []
    for pkg_name in pkg_names:
        pkg_path = Path(pkg_name)
        if _git.has_uncommitted_changes(pkg_path):
            error_msg = 'uncommitted changes, skipping package'
            print_status_output(pkg_name, is_error=True, msg=error_msg)
            continue
        _git.switch_to_branch(branch_name, pkg_path)

        if is_koji_build:
            if arguments['--scratch']:
                build = trigger_koji_build(pkg_path, scratch=True)
            elif arguments['--build']:
                # TODO: check also that sources file is updated!
                build = trigger_koji_build(pkg_path, scratch=False)
        elif arguments['--mock']:
            build = trigger_mock_build(pkg_path, wait=True)
            _handle_build_completion(build, [build])
            build = None
        elif arguments['--copr']:
            build = trigger_copr_build(pkg_path, copr_repo)
        if build is not None:
            builds_in_progress.append(build)

    for build in builds_in_progress:
        if build.url:
            print(f'{build.pkg_name}: {build.url}')
    _wait_for_build_completion(builds_in_progress)


if __name__ == '__main__':
    main()

