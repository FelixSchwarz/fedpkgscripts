
import importlib

_shell = importlib.import_module('shell-utils')
run_cmd = _shell.run_cmd
print_status_output = _shell.print_status_output


def get_version_from_specfile(pkg_path, pkg_name):
    rpmspec_cmd = ['/usr/bin/rpmspec', '-q', '--srpm', '--qf', '%{version}', f'{pkg_name}.spec']
    rpmspec_proc = run_cmd(rpmspec_cmd, working_directory=pkg_path, wait=True, exit_on_error=False)
    if rpmspec_proc.returncode != 0:
        error = 'error while retrieving previous version from spec file'
        print_status_output(pkg_name, is_error=True, msg=error)
        return
    old_version = rpmspec_proc.stdout.read().decode('utf8').strip()
    return old_version
