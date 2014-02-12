# coding: utf-8
from __future__ import with_statement
import os.path
import tempfile
from datetime import datetime
import codecs
import sys

from fabric.api import run, local, env, put, cd, warn
from taskset import TaskSet, task_method

from fab_deploy import utils

class PseudoVcs(TaskSet):
    BRANCH_OPTION = None

    def _extract_from_hgignore(self):
        """ Extracts list of exclusion patterns from .hgignore file. """
        excluded = []
        try:
            for str in codecs.open('.hgignore', 'rb', sys.getdefaultencoding()):
                str = str.strip()
                if str.startswith(('#', 'syntax: glob')) or str=='':
                    continue
                elif str=='syntax: regexp':
                    raise NotImplementedError('Regexp syntax is not supported.')
                else:
                    if str.startswith('*'):
                        excluded.append(str)
                    else:
                        excluded.append(utils._project_path(str))
        except IOError as e:
           warn('.hgignore file was not found. Nothing is excluded.')
        return excluded

    def _exclude_string(self):
        excludes = self._extract_from_hgignore()
        exclude_string = " ".join(['--exclude="%s"' % pattern for pattern in excludes])
        if os.path.exists('.excludes'):
            exclude_string =  "-X .excludes " + exclude_string
        return exclude_string

    @task_method
    def push(self, branch=None):
        """
        Upload the current project to a remote system, tar/gzipping during the move.
        Files listed at :file:`<project root>/.exclude` file wouldn't be uploaded
        (glob patterns are supported in .exclude file).

        This function makes use of the ``/tmp/`` directory and the ``tar`` and
        ``gzip`` programs/libraries; thus it will not work too well on Win32
        systems unless one is using Cygwin or something similar.

        This should be using ``fabric.contrib.project.upload_project``
        but upload_project doesn't support excludes.
        """
        tar_file = os.path.join(
            tempfile.gettempdir(),
            "fab.%s.tar" % datetime.utcnow().strftime('%Y_%m_%d_%H-%M-%S')
        )
        tarCommand = "tar %s -czf %s ." % (self._exclude_string(), tar_file)
        local(tarCommand)
        tgz_name = env.conf.SRC_DIR + '/' + env.conf.INSTANCE_NAME + ".tar.gz"
        put(tar_file, tgz_name)
        os.remove(tar_file)
        with cd(env.conf.SRC_DIR):
            run("tar -xzf " + tgz_name)
            run("rm -f " + tgz_name)

    @task_method
    def configure(self):
        pass

    @task_method
    def init(self):
        pass

    @task_method
    def up(self, branch):
        pass

instance = PseudoVcs()
__all__ = instance.expose_to_current_module()