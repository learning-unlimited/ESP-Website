# coding: utf-8
from __future__ import with_statement, absolute_import

from fabric.api import env, run, settings, sudo, hide, abort
from fabric.contrib import files, console

from taskset import task_method
from fab_deploy import utils
from fab_deploy import system
from fab_deploy.webserver.wsgi_backend import WsgiBackend

__all__ = ['Apache']

APACHE_PORTS_FILE = '/etc/apache2/ports.conf'
TAKEOVER_STRING = '# This file is managed by django-fab-deploy. "Listen" directives are in /etc/apache2/sites-available/*'
OLD_TAKEOVER_STRING = '# This file is managed by django-fab-deploy. Please do not edit it manually.'

class Apache(WsgiBackend):

    def __init__(self, config='apache.config', wsgi='wsgi.py'):
        super(Apache, self).__init__(wsgi)
        self.config = config

    def _get_server_config_name(self):
        return '%s_%s' % (env.conf['INSTANCE_NAME'], self.config)

    @task_method
    @utils.run_as_sudo
    def upload_config(self):
        """ Updates apache config. """
        name = self._get_server_config_name()
        utils.upload_config_template(self.config,
                                     '/etc/apache2/sites-available/%s' % name,
                                     extra_context={'CURRENT_BACKEND': self},
                                     use_sudo=True)
        sudo('a2ensite %s' % name)

    @task_method
    @utils.run_as_sudo
    def remove_config(self):
        """ Removes apache config and reloads apache. """
        name = self._get_server_config_name()
        sudo('a2dissite %s' % name)
        sudo('rm -f /etc/apache2/sites-available/'+name)
        sudo('invoke-rc.d apache2 reload')

    @task_method
    @utils.run_as_sudo
    def restart(self):
        """ Restarts apache using init.d script. """
        # restart is not used because it can leak memory in some cases
        # without pty=False restart silently fails on Ubuntu 10.04.
        sudo('invoke-rc.d apache2 stop', pty=False)
        sudo('invoke-rc.d apache2 start', pty=False)

    @task_method
    def update_config(self):
        """ Updates apache config, wsgi script and restarts apache. """
        self.upload_config()
        self.upload_wsgi()
        self.restart()

    @task_method
    @utils.run_as_sudo
    def is_running(self):
        """
        Returns whether apache is running
        """
        with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
            output = sudo('invoke-rc.d apache2 status')
        return output.succeeded

    # ==== installation ===

    @task_method
    @utils.run_as_sudo
    def install(self, confirm=True):
        """ Installs apache. """
        system.aptitude_install('apache2 libapache2-mod-wsgi libapache2-mod-rpaf locales-all')
        self.setup_locale()

        default_sites = [
            '/etc/apache2/sites-enabled/default',
            '/etc/apache2/sites-enabled/000-default',
        ]

        for site in default_sites:
            if files.exists(site, use_sudo=True):
                msg = "Remote %s will be deleted.\n" \
                      "This is necessary for django-fab-deploy to work.\n" \
                      "Choose 'n' and do a backup if you have customized this file.\n"\
                      "Do you wish to continue?"  % site
                if not confirm or console.confirm(msg):
                    sudo('rm -f %s' % site)
                else:
                    abort("Aborting.")


        if _ports_conf_needs_disabling():
            msg = "The contents of remote %s will be erased.\n"\
                  "This is necessary for django-fab-deploy to work.\n" \
                  "Choose 'n' and do a backup if you have customized this file.\n" \
                  "Do you wish to continue?" % APACHE_PORTS_FILE
            if not confirm or console.confirm(msg):
                _disable_ports_conf()
            else:
                abort("Aborting.")

    @task_method
    @utils.run_as_sudo
    def setup_locale(self):
        """ Setups apache locale. Apache is unable to handle file uploads with
        unicode file names without this. """
        files.append('/etc/apache2/envvars',
                     ['export LANG="en_US.UTF-8"', 'export LC_ALL="en_US.UTF-8"'],
                     use_sudo=True)

# === automatic apache ports management ===

@utils.run_as_sudo
def _ports_conf_needs_disabling():
    lines = _ports_lines()
    if lines[0] == TAKEOVER_STRING:
        return False
    if lines[0] == OLD_TAKEOVER_STRING:
        # ports.conf from old DFD versions should be harmless
        # and it is necessary to preserve it if there are sites managed by
        # DFD < 0.8 on the same server.
        return False
    return True


@utils.run_as_sudo
def _disable_ports_conf():
    sudo("echo '%s\n' > %s" % (TAKEOVER_STRING, APACHE_PORTS_FILE))

#@task
@utils.run_as_sudo
def _ports_lines():
    with settings(hide('stdout')):
        ports_data = sudo('cat ' + APACHE_PORTS_FILE)
    return ports_data.splitlines()
