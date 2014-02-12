from __future__ import absolute_import
from fabric.api import *
from fabtest import fab
from fab_deploy.utils import run_as
from fab_deploy.system import create_sudo_linux_account
from .base import FabDeployTest
from ..utils import public_key_path, setup_sudo

@run_as('root')
def whoami():
    return run('whoami')

class BasicTest(FabDeployTest):
    def test_run_as(self):
        user = fab(whoami)
        self.assertEqual(user, 'root')

    def test_create_sudo_linux_account(self):
        setup_sudo()
        fab(create_sudo_linux_account, public_key_path(), 'testsudo')

        @run_as('testsudo')
        def whoami():
            return run('whoami')

        user = fab(whoami)
        self.assertEqual(user, 'testsudo')

        @run_as('testsudo')
        def test_sudo():
            return run('sudo aptitude update')

        fab(test_sudo)
