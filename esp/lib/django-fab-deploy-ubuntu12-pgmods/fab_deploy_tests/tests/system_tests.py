# coding: utf-8
from __future__ import absolute_import
from fabric.api import run, env, abort
from fabtest import fab, FabricAbortException

from fab_deploy.utils import run_as
from fab_deploy.system import prepare, ssh_add_key

from fab_deploy_tests.utils import setup_ssh, public_key_path, setup_sudo
from .base import FabDeployTest

@run_as('root')
def setup_root_ssh():
    ssh_add_key(public_key_path())

@run_as('root')
def whoami():
    return run('whoami')

class AbortTest(FabDeployTest):
    # This test really belongs to fabtest package.
    # It tests fabtest.fab exception handling.
    def test_abort(self):
        def this_should_be_catched():
            fab(abort, 'aborted')
        self.assertRaises(FabricAbortException, this_should_be_catched)


class SshTest(FabDeployTest):
    def test_python(self):
        self.assertPackageInstalled('python-minimal')

    def test_create_linux_account(self):
        setup_sudo()
        setup_ssh()
        def command():
            self.assertUserIs('foo')
        fab(command)

    def test_add_ssh_key(self):
        fab(setup_root_ssh)
        env.password = None # should use ssh key
        self.assertEqual(fab(whoami), 'root')


class PrepareServerTest(FabDeployTest):
    def test_prepare_server_ok(self):
        setup_sudo()
        setup_ssh()

        fab(prepare)
        self.assertPackageInstalled('python')
        apps = self.project.apps
        fab(apps.django.backend.install, confirm=False)
        fab(apps.django.frontend.install)
        self.assertPackageInstalled('nginx')
        self.assertPackageInstalled('apache2')


class FastPrepareServerTest(PrepareServerTest):
    snapshot = 'fabtest-prepared-server'

