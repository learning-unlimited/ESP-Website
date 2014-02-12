# coding: utf-8
from __future__ import absolute_import

from fabric.api import env
from fabtest import fab

from fab_deploy import pip
from .deploy import FabDeployProjectTest
from ..utils import setup_ssh, setup_sudo
from ..test_project2.fabfile import foo_site as foo_site2, project as project2

class NoPipSetupTest(FabDeployProjectTest):
    def test_no_pip_conf(self):
        self.assertNoFile(env.conf.HOME_DIR+'/.pip/pip.conf')
        fab(pip.setup_conf)
        self.assertNoFile(env.conf.HOME_DIR+'/.pip/pip.conf')

class PipSetupTest(FabDeployProjectTest):
    project_dir = 'test_project2'
    project = project2

    def test_pip_conf(self):
        """ FIXME: The test is not valid due to inner contradiction. """
        fab(foo_site2)
        setup_sudo()
        setup_ssh()

        self.assertNoFile(env.conf.HOME_DIR+'/.pip/pip.conf')
        fab(pip.setup_conf)
        self.assertFileExists(env.conf.HOME_DIR+'/.pip/pip.conf')
