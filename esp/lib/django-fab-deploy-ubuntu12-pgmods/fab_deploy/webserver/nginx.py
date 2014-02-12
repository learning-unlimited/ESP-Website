# coding: utf-8
from __future__ import with_statement

from fabric.api import  env, settings, sudo
from taskset import TaskSet, task_method

from fab_deploy import utils
from fab_deploy import system

__all__ = ['Nginx']

class Nginx(TaskSet):

    def __init__(self, config='nginx.config'):
        self.config = config

    def _get_server_config_name(self):
        return '%s_%s' % (env.conf['INSTANCE_NAME'], self.config)

    @task_method
    @utils.run_as_sudo
    def install(self):
        """ Installs nginx. """
        os = utils.detect_os()
        options = {'lenny': '-t lenny-backports'}
        system.aptitude_install('nginx', options.get(os, ''))
        sudo('rm -f /etc/nginx/sites-enabled/default')

    @task_method
    @utils.run_as_sudo
    def update_config(self):
        """ Updates nginx config and restarts nginx. """
        name = self._get_server_config_name()
        utils.upload_config_template(self.config,
                                     '/etc/nginx/sites-available/%s' % name,
                                     use_sudo=True)
        with settings(warn_only=True):
            sudo('ln -s /etc/nginx/sites-available/%s /etc/nginx/sites-enabled/%s' % (name, name))
        sudo('invoke-rc.d nginx restart')

    @task_method
    @utils.run_as_sudo
    def remove_config(self):
        """ Removes nginx config and reloads nginx. """
        name = self._get_server_config_name()
        sudo('rm -f /etc/nginx/sites-enabled/'+name)
        sudo('rm -f /etc/nginx/sites-available/'+name)
        sudo('invoke-rc.d nginx reload')
