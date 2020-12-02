
import importlib
import os
import subprocess
import sys
import time

import colorama


__all__ = [
    'display_output',
    'run_cmd',
    'sanitize_pkg_names',
]

colorama_color = importlib.import_module('colorama-utils').colorama_color

def display_output(stdout, stderr, *, header_str=None):
    _c = colorama
    if header_str:
        with colorama_color(_c.Fore.YELLOW):
            print(header_str)
    if stdout:
        try:
            stdout_str = stdout.decode('utf8')
            print(stdout_str)
        except UnicodeDecodeError:
            print(stdout)
    with colorama_color(_c.Fore.RED, _c.Style.BRIGHT):
        if stderr:
            try:
                stderr_str = stderr.decode('utf8')
                print(stderr_str)
            except UnicodeDecodeError:
                print(stderr)


def print_in_progress(pkg_name, msg='', newline=False):
    suffix = f'  {msg}' if msg else ''

    sys.stdout.write('\r')
    print(f'{pkg_name} …{suffix}', end='\n' if newline else '')
    sys.stdout.flush()


def print_status_output(pkg_name, *, is_error=False, is_warning=False, msg=''):
    if is_error:
        status_colors = (colorama.Fore.RED, colorama.Style.BRIGHT)
        status_str = '✗'
    elif is_warning:
        status_colors = (colorama.Fore.YELLOW, )
        status_str = '?'
    else:
        status_colors = (colorama.Fore.GREEN, )
        status_str = '✓'
    if msg and not msg.startswith(': '):
        msg = ': ' + msg
    sys.stdout.write('\r')
    with colorama_color(*status_colors):
        print(f'{status_str} {pkg_name}{msg}')
    sys.stdout.flush()


def run_cmd(cmd, *, working_directory=None, dry_run=False, wait=False, exit_on_error=True):
    if dry_run:
        print(cmd)
        return
    env = {
        'HOME': os.getenv('HOME'),
        'LANG': 'C',
    }
    proc = subprocess.Popen(
        cmd,
        shell=False,
        env=env,
        cwd=working_directory,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if wait:
        proc.wait()
    else:
        time.sleep(0.1)
        proc.poll()
    if proc.returncode not in (None, 0):
        cmd_str = ' '.join(cmd)
        display_output(proc.stdout.read(), proc.stderr.read(), header_str=cmd_str)
        if exit_on_error:
            sys.exit(20)
    return proc


def sanitize_pkg_names(names):
    pkg_names = []
    for name in names:
        if name.endswith('/'):
            name = name[:-1]
        pkg_names.append(name)
    return pkg_names

