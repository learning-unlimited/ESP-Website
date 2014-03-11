# coding: utf-8
from __future__ import with_statement

from abc import ABCMeta, abstractmethod

from fabric.api import abort, run, env
from taskset import TaskSet, task_method

from fab_deploy import utils

class StaticSite(TaskSet):

    def __init__(self, frontend):
        self.frontend = frontend

    def expose_as_module(self, module_name):
        module = super(StaticSite, self).expose_as_module(module_name)
        module.frontend = self.frontend.expose_as_module('frontend')
        return module

    @task_method
    def deploy(self):
        """ Deploys project on prepared server. """
        self.update_web_servers()

    @task_method
    def update_web_servers(self):
        """ Updates frontend config. """
        self.frontend.update_config()

    @task_method
    def install_web_servers(self):
        """ Install frontend software. """
        self.frontend.install()

    @task_method
    def restart(self):
        # nothing to do in a static site case
        pass

    @task_method
    def remove(self):
        """ Removes application traces.
        
        Is prohibited to remove app's code since several appications may share
        single VCS repository.
        """
        self.frontend.remove_config()


class WebApp(StaticSite):
    __metaclass__ = ABCMeta

    def __init__(self, frontend, backend):
        super(WebApp, self).__init__(frontend)
        self.backend = backend

    def expose_as_module(self, module_name):
        module = super(WebApp, self).expose_as_module(module_name)
        module.backend = self.backend.expose_as_module('backend')
        return module

    @task_method
    def deploy(self):
        """ Deploys application on prepared server. """
        self.update_web_servers()
        self.update_config()
    
        self.syncdb()
        self.migrate()

    @task_method
    def update_web_servers(self):
        """ Updates frontend and backend configs. """
        # TODO: detect the reason why apache should be restarted before nginx
        # DO NOT try to invert the order - you'll fail
        self.backend.update_config()
        super(WebApp, self).update_web_servers()

    @task_method
    def install_web_servers(self):
        """ Installs frontend and backend software. """
        self.backend.install()
        super(WebApp, self).install_web_servers()

    @task_method
    def restart(self):
        """ Restarts web application.
        
        Usually by touching conf file or restarting backend.
        """
        # need this check assuming non-wsgi backends in the future
        if hasattr(self.backend, 'touch'):
            self.backend.touch()
        else:
            self.backend.restart()

    @task_method
    def remove(self):
        """ Removes application traces.
        
        Is prohibited to remove app's code since several appications may share
        single VCS repository.
        """
        super(WebApp, self).remove()
        self.backend.remove_config()

    @task_method
    @abstractmethod
    def update_config(self, restart=True):
        """ Updates config of the web application. """
        pass

    @task_method
    @abstractmethod
    def syncdb(self, params=''):
        pass

    @task_method
    @abstractmethod
    def migrate(self, params='', do_backup=True):
        pass

    @task_method
    @utils.inside_project
    @abstractmethod
    def test(self, what=''):
        """ Launches tests for the web application. """
        pass
