# coding: utf-8
from fabric.api import run, local, env, settings, abort
from fabric.contrib.console import confirm
from taskset import TaskSet, task_method

from fab_deploy.utils import upload_config_template

class Hg(TaskSet):
    BRANCH_OPTION = 'HG_BRANCH'

    @task_method
    def init(self):
        run('hg init')

    @task_method
    def up(self, branch):
        run('hg up -C ' + branch)

    @task_method
    def push(self, branch=None):
        with settings(warn_only=True):
            res = local('hg push ssh://%s/src/%s/ --new-branch' % (env.hosts[0], env.conf.INSTANCE_NAME))
            if res.failed:
                if not confirm("Error occured during push. Continue anyway?", default=False):
                    abort("Aborting.")

    @task_method
    def configure(self):
        upload_config_template('hgrc', env.conf.SRC_DIR + '/.hg/hgrc',
                               skip_unexistent=True)

instance = Hg()
__all__ = instance.expose_to_current_module()