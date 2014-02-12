import os.path
from fabric.api import run
from fabtest import fab
from fab_deploy.utils import run_as
from fab_deploy.system import create_linux_account, install_sudo, create_sudo_linux_account

def public_key_path():
    return os.path.join(os.path.dirname(__file__), 'keys', 'id_rsa.pub')

def private_key_path():
    return os.path.join(os.path.dirname(__file__), 'keys', 'id_rsa')

def get_package_state(name):
    """ Returns package state as in aptitude output: i, v, etc. """
    @run_as('root')
    def command():
        regexp = "^%s$" % name
        output = run('aptitude -q -F "%%c" search %s' % regexp)
        return output.splitlines()[-1]
    return fab(command)

def setup_ssh():
    fab(create_linux_account, public_key_path())

def setup_sudo():
    fab(install_sudo)
    fab(create_sudo_linux_account, public_key_path())
