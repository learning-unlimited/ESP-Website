# coding: utf-8
from __future__ import with_statement
from functools import wraps
import types

from fabric.api import abort, settings, cd, run, env, puts, sudo
from fabric.contrib import console
from taskset import TaskSet, task_method

from fab_deploy import utils, pip, system, vcs, db
from fab_deploy.webserver.apache import Apache
from fab_deploy.webserver.nginx import Nginx
from fab_deploy.django import Django

__all__ = ['WebProject']

class WebProject(TaskSet):

    def __init__(self, apps=None):
        if apps is None:
            apps = dict(django=Django(Nginx(), Apache(wsgi='django_wsgi.py')))
        self.apps = apps

    def _expose_to(self, module_obj):
        task_list = super(WebProject, self)._expose_to(module_obj)
        apps_module = types.ModuleType('apps')
        for app_name, app in self.apps.iteritems():
            module = app.expose_as_module(app_name)
            setattr(apps_module, app_name, module)
        module_obj.apps = apps_module
        task_list.append('apps')
        return task_list

    @task_method
    def full_deploy(self):
        """ Prepares server and deploys the project. """
        os = utils.detect_os()
        if not console.confirm("Is the OS detected correctly (%s)?" % os, default=False):
            abort("Detection fails. Please set env.conf.OS to correct value.")
        system.prepare()
        self.install_web_servers()
        self.install_databases()
        self.deploy()

    @task_method
    def install_web_servers(self):
        """ Installs servers for all of the project apps. """
        for app in self.apps.itervalues():
            app.install_web_servers()

    @task_method
    def install_databases(self):
        """ Installs project's databases. """
        # stays trivial while database is single
        database = db.get_backend()
        database.install()

    @task_method
    def install_r(self, what=None, options='', restart=True):
        """
        Installs pip requirements listed in ``<PIP_REQUIREMENTS_PATH>/<file>.txt`` file
        and reloads all apps of the project, if specified.
        """
        pip.install_r(what, options)
        if restart:
            for app in self.apps.itervalues():
                app.restart()

    @task_method
    def update_r(self, what=None, options='', restart=True):
        """
        Updates pip requirements listed in ``<PIP_REQUIREMENTS_PATH>/<file>.txt`` file
        and reloads all apps of the project, if specified.
        """
        pip.update_r(what, options)
        if restart:
            for app in self.apps.itervalues():
                app.restart()

    @task_method
    def deploy(self):
        pip.virtualenv_create()
        self._make_clone()
        self.install_r(env.conf.PIP_REQUIREMENTS, restart=False)
        for app in self.apps.itervalues():
            app.deploy()

    @task_method
    def _make_clone(self):
        """ Creates repository clone on remote server. """
        run('mkdir -p ' + env.conf.SRC_DIR)
        with cd(env.conf.SRC_DIR):
            with settings(warn_only=True):
                vcs.init()
        vcs.push()
        with cd(env.conf.SRC_DIR):
            vcs.up()
        #self.update_config(restart=False)
        vcs.configure()

    @task_method
    def remove(self, confirm=True):
        """ Shuts site down. This command doesn't clean everything, e.g.
        user data (database, backups) is preserved. """

        if confirm:
            message = "Do you wish to undeploy host %s?" % env.hosts[0]
            if not console.confirm(message, default=False):
                abort("Aborting.")
        for app in self.apps.itervalues():
            app.remove()
        # remove project sources
        run('rm -rf %s' % env.conf.SRC_DIR)
        # remove parts of project's virtualenv
        for folder in ['bin', 'include', 'lib', 'src']:
            run('rm -rf %s' % env.conf.ENV_DIR + '/' + folder)

    @task_method
    def update_web_servers(self):
        for app in self.apps.itervalues():
            app.update_web_servers()

    @task_method
    def up(self, branch=None, before_restart=lambda: None):
        """ Runs vcs ``up`` or ``checkout`` command on server and reloads
        mod_wsgi process. """
        utils.delete_pyc()
        with cd('src/' + env.conf['INSTANCE_NAME']):
            vcs.up(branch)
        before_restart()
        for app in self.apps.itervalues():
            app.restart()
    
    @task_method
    def push(self, *args, **kwargs):
        ''' Run it instead of your VCS push command.
    
        The following strings are allowed as positional arguments:
    
        * 'notest' - don't run tests
        * 'syncdb' - run syncdb before code reloading
        * 'migrate' - run migrate before code reloading
        * 'pip_update' - run virtualenv.update_r before code reloading
        * 'norestart' - do not reload source code
    
        Keyword arguments:
    
        * before_restart - callable to be executed after code uploading
          but before the web server reloads the code.
    
        Customization example can be found  :ref:`here <fab-push-customization>`.
    
        '''
        allowed_args = set(['notest', 'syncdb', 'migrate', 'pip_update', 'norestart'])
        for arg in args:
            if arg not in allowed_args:
                puts('Invalid argument: %s' % arg)
                puts('Valid arguments are: %s' % allowed_args)
                return
    
        vcs.push()
        utils.delete_pyc()
        with cd('src/' + env.conf['INSTANCE_NAME']):
            vcs.up()
    
        if 'pip_update' in args:
            self.update_r(restart=False)
        for app in self.apps.itervalues():
            if 'syncdb' in args:
                app.syncdb()
            if 'migrate' in args:
                app.migrate()
        # execute 'before_restart' callback
        kwargs.get('before_restart', lambda: None)()
        for app in self.apps.itervalues():
            if 'norestart' not in args:
                app.restart()
            if 'notest' not in args:
                app.test()
