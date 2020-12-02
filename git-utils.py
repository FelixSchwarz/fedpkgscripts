
import importlib
from pathlib import Path


__all__ = ['has_uncommitted_changes']

_shell_utils = importlib.import_module('shell-utils')

display_output = _shell_utils.display_output
run_cmd = _shell_utils.run_cmd

def has_uncommitted_changes(pkg_path):
    proc = run_cmd(['/usr/bin/git', 'ls-files', '--modified'], working_directory=pkg_path, wait=True)
    return bool(proc.stdout.read())

def has_unpushed_changes(pkg_path):
    proc = run_cmd(['/usr/bin/git', 'cherry'], working_directory=pkg_path, wait=True)
    return bool(proc.stdout.read())

def fetch_remote_changes(pkg_path):
    proc = run_cmd(['/usr/bin/git', 'fetch'], working_directory=pkg_path, wait=True)
    fetched_new_changes = bool(proc.stdout.read())
    return fetched_new_changes

def push_branch(target_branch, pkg_path):
    switch_to_branch(target_branch, pkg_path)
    run_cmd(['/usr/bin/git', 'push',], working_directory=pkg_path, wait=True)

def pull(remote, pkg_path, *, ff_only):
    assert ff_only
    cmd = ['/usr/bin/git', 'pull', '--ff-only', remote]
    run_cmd(cmd, working_directory=pkg_path, wait=True)

def switch_to_branch(target_branch, pkg_path):
    run_cmd(['/usr/bin/git', 'checkout', target_branch], working_directory=pkg_path, wait=True)
    return True

