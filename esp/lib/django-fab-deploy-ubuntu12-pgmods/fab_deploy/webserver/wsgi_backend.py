# coding: utf-8
from __future__ import with_statement, absolute_import
import posixpath

from fabric.api import env, run

from taskset import TaskSet, task_method
from fab_deploy import utils

class WsgiBackend(TaskSet):
    """ Base class for backends using wsgi. """

    def __init__(self, wsgi):
        self.wsgi = wsgi

    def get_wsgi_dir(self):
        return posixpath.join(
            env.conf['ENV_DIR'], 'var', 'wsgi', env.conf['INSTANCE_NAME']
        )

    def get_wsgi_file_name(self):
        """ Returns remote filename of the wsgi file. """
        return self.wsgi

    def get_wsgi_full_file_name(self):
        """ Returns full remote filename of the wsgi file (with path). """
        return posixpath.join(self.get_wsgi_dir(), self.get_wsgi_file_name())

    @task_method
    def touch(self, wsgi_file=None):
        """
        Reloads source code by touching the wsgi file.

        If backend doesn't have this feature then this method must be
        overriden to provide same effect in other way (restart, reload, etc).
        """
        if wsgi_file is None:
            wsgi_file = self.get_wsgi_full_file_name()
        run('touch ' + wsgi_file)

    @task_method
    def upload_wsgi(self):
        """ Uploads wsgi deployment script. """
        wsgi_dir = self.get_wsgi_dir()
        run('mkdir -p ' + wsgi_dir)
        utils.upload_config_template(
            self.wsgi,
            posixpath.join(wsgi_dir, self.get_wsgi_file_name())
        )