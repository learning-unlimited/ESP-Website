# coding: utf-8
from fabric.api import env, run, local
from taskset import TaskSet, task_method

class Git(TaskSet):
    BRANCH_OPTION = 'GIT_BRANCH'

    @task_method
    def init(self):
        run('git init')
        run('git config receive.denyCurrentBranch ignore') # allow update current branch

    @task_method
    def up(self, branch):
        run('git checkout --force %s' % branch) # overwrite local changes

    @task_method
    def push(self, branch=None):
        user, host = env.hosts[0].split('@')
        local('git push --force ssh://%s/~%s/src/%s/ %s' % (env.hosts[0], user,
            env.conf.INSTANCE_NAME, branch or env.conf[self.BRANCH_OPTION]))

    @task_method
    def configure(self):
        pass

instance = Git()
__all__ = instance.expose_to_current_module()