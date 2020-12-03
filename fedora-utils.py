
import subprocess

def has_kerberos_ticket():
    rc = subprocess.call(['/usr/bin/klist', '-s'])
    return (rc == 0)

