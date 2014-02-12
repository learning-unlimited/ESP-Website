# coding: utf-8
from __future__ import with_statement

from fabric.api import run, env, cd, task

from fab_deploy import utils
# FIXME: this shouldn't be apache-centered
from fab_deploy.webserver import apache

__all__ = ['pip', 'install_r', 'update_r', 'setup_conf']

@task(default=True)
@utils.inside_src
def pip(commands=''):
    """ Runs pip command """
    run('pip ' + commands)

@task
@utils.inside_src
def install_r(what=None, options=''):
    """ Installs pip requirements listed in ``<PIP_REQUIREMENTS_PATH>/<file>.txt`` file. """
    what = utils._pip_req_path(what or env.conf.PIP_REQUIREMENTS_ACTIVE)
    run('pip install %s -r %s' % (options, what))

@task
@utils.inside_src
def update_r(what=None, options=''):
    """ Updates pip requirements listed in ``<PIP_REQUIREMENTS_PATH>/<file>.txt`` file. """
    what = utils._pip_req_path(what or env.conf.PIP_REQUIREMENTS_ACTIVE)
    run('pip install %s -U -r %s' % (options, what))

@task
def setup_conf(username=None):
    """ Sets up pip.conf file """
    username = username or env.conf.USER
    home_dir = utils.get_home_dir(username)

    @utils.run_as(username)
    def do_setup_conf():
        run('mkdir --parents %s.pip' % home_dir)
        utils.upload_config_template('pip.conf',
            home_dir + '.pip/pip.conf', skip_unexistent=True)

    do_setup_conf()

@task
def virtualenv_create(name=None):
    run('mkdir -p envs')
    if name is None:
        name = env.conf['INSTANCE_NAME']
    with cd('envs'):
        run('virtualenv --no-site-packages %s' % name)
