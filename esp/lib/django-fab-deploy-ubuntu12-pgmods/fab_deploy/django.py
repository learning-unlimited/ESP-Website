# coding: utf-8
from __future__ import with_statement

from fabric.api import run, settings, env, hide, warn
from fabric.contrib import files
from taskset import task_method

from fab_deploy.apps import WebApp
from fab_deploy import utils
from fab_deploy import db

__all__ = ['Django']

class Django(WebApp):

    def __init__(self, frontend, backend, local_config='config.py', remote_config='config.server.py'):
        super(Django, self).__init__(frontend, backend)
        self.local_config = local_config
        self.remote_config = remote_config

    @task_method
    def update_config(self, restart=True):
        """ Updates :file:`config.py` on server (using :file:`config.server.py`) """
        files.upload_template(
            utils._project_path(self.remote_config),
            utils._remote_project_path(self.local_config),
            env.conf, True
        )
        if restart:
            self.backend.touch()

    @task_method
    @utils.inside_project
    def command_is_available(self, command):
        with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
            output = run('python manage.py help ' + command)
    
        if output.succeeded:
            return True
    
        # that's ugly
        unknown_command_msg = "Unknown command: '%s'" % command
        if unknown_command_msg in output:
            return False
    
        # re-raise the original exception
        run('python manage.py help ' + command)
    
    @task_method
    @utils.inside_project
    def manage(self, command):
        """
        Runs django management command. Example::
    
            fab manage:createsuperuser
    
        """
        command_name = command.split()[0]
        if not self.command_is_available(command_name):
            warn('Management command "%s" is not available' % command_name)
        else:
            run('python manage.py ' + command)
    
    @task_method
    def migrate(self, params='', do_backup=True):
        """ Runs migrate management command. Database backup is performed
        before migrations until ``do_backup=False`` is passed. """
        if do_backup:
            database = db.get_backend()
            backup_dir = env.conf['ENV_DIR'] + '/var/backups/before-migrate'
            run('mkdir -p ' + backup_dir)
            database.dump(backup_dir)
        self.manage('migrate --noinput %s' % params)
    
    @task_method
    def syncdb(self, params=''):
        """ Runs syncdb management command. """
        self.manage('syncdb --noinput %s' % params)
    
    @task_method
    def compress(self, params=''):
        with settings(warn_only=True):
            self.manage('synccompress %s' % params)
    
    @task_method
    def collectstatic(self, params=''):
        self.manage('collectstatic --noinput %s' % params)
    
    @task_method
    @utils.inside_project
    def test(self, what=''):
        """
        Runs 'runtests.sh' script from project root.
        Example runtests.sh content::
    
            #!/bin/sh
    
            default_tests='accounts forum firms blog'
            if [ $# -eq 0 ]
            then
                ./manage.py test $default_tests --settings=test_settings
            else
                ./manage.py test $* --settings=test_settings
            fi
        """
        with settings(warn_only=True):
            run('./runtests.sh ' + what)

#def coverage():
#    pass
#    with cd(env.conf['SRC_DIR']):
#        run('source %s/bin/activate; ./bin/runcoverage.sh' % env.conf['ENV_DIR'])

