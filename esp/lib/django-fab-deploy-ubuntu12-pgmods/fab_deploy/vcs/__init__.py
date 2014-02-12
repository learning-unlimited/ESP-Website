# coding: utf-8
from __future__ import absolute_import
import warnings

from fabric.api import env, task
from taskset import TaskSet

def get_vcs():
    """ Returns a module with current VCS """
    vcs = env.conf.VCS
    if isinstance(vcs, TaskSet):
        return vcs

    # XXX: deprecate string-based VCS configuration?
    # warnings.warn("string-base vcs configuration is deprecated", DeprecationWarning)

    name = vcs
    mod = __import__(name, fromlist=name.split('.')[1:])
    return mod.instance

@task
def push(branch=None):
    get_vcs().push(branch or default_branch())

@task
def up(branch=None):
    get_vcs().up(branch or default_branch())

@task
def init():
    get_vcs().init()

@task
def configure():
    get_vcs().configure()

def default_branch():
    return env.conf.get(get_vcs().BRANCH_OPTION, None)
