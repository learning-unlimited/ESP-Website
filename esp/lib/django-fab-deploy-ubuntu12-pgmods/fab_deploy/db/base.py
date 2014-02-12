# coding: utf-8
from __future__ import absolute_import
import posixpath
from datetime import datetime

from fabric.contrib import console
from fabric.api import env, run, abort, prompt, warn
from fabric.context_managers import settings, hide
from fabric.utils import puts
from taskset import TaskSet, task_method

from fab_deploy import utils

__all__ = ['Database']

class Database(TaskSet):
    name = 'Database'

    CREATE_USER_SQL = None
    CREATE_DB_SQL = None
    DROP_DB_SQL = "DROP DATABASE %(db_name)s;"
    DROP_USER_SQL = "DROP ROLE %(db_user)s;"
    GRANT_PERMISSIONS_SQL = None
    USER_EXISTS_SQL = None

    SUPERUSER = 'root'

    def _get_root_password(self):
        """ Asks root password (only once, if needed) """
        if env.conf.get('DB_ROOT_PASSWORD', None) is None:
            env.conf.DB_ROOT_PASSWORD = prompt('Please enter %s root password:' % self.name)
        return env.conf.DB_ROOT_PASSWORD

    def _credentials(self, db_name=None, db_user=None, db_password=None):
        """ Returns db credentials (respecting env.conf defaults) """
        db_name = db_name or env.conf.DB_NAME
        db_user = db_user or env.conf.DB_USER
        if db_password is None:
            db_password = env.conf.DB_PASSWORD
        return db_name, db_user, db_password

    @task_method
    def is_installed(self):
        raise NotImplementedError()

    @task_method
    def execute_sql(self, sql, user=None, password=None, db_name=None):
        """ Executes passed sql command. """
        raise NotImplementedError()

    @task_method
    def _user_exists(self, db_user):
        sql = self.USER_EXISTS_SQL % dict(db_user=db_user)
        with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
            result = self.execute_sql(sql, self.SUPERUSER)
        return result.succeeded

    @task_method
    def _db_exists(self, db_name):
        raise NotImplementedError()

    @task_method
    def create_user(self, db_user=None, db_password=None):
        """ Creates database user. """
        _, db_user, db_password = self._credentials(None, db_user, db_password)

        if db_user == self.SUPERUSER: # do we really need this?
            abort('Root %s user can not be created' % self.name)
            return

        if self._user_exists(db_user):
            puts('%s user %s already exists' % (self.name, db_user))
            return

        sql = self.CREATE_USER_SQL % dict(db_user=db_user, db_password=db_password)
        return self.execute_sql(sql, self.SUPERUSER)

    @task_method
    def create_db(self, db_name=None, db_user=None, root_password=None):
        """ Creates an empty database. """
        db_name, db_user, _ = self._credentials(db_name, db_user, None)

        sql = self.CREATE_DB_SQL % dict(db_name=db_name, db_user=db_user)
        self.execute_sql(sql, self.SUPERUSER, root_password)

        # XXX: really?
        if db_user != self.SUPERUSER:
            self.create_user(db_user=db_user)
            self.grant_permissions(db_name=db_name, db_user=db_user)

    @task_method
    def drop_db(self, db_name=None, confirm=True):
        db_name, _, _ = self._credentials(db_name, None, None)
        question = "Really drop database %s?" % db_name
        if confirm and not console.confirm(question, default=False):
            return
        sql = self.DROP_DB_SQL % dict(db_name=db_name)
        self.execute_sql(sql, self.SUPERUSER)

    @task_method
    def drop_user(self, db_user=None, confirm=True):
        _, db_user, _ = self._credentials(None, db_user, None)
        question = "Really drop user %s?" % db_user
        if confirm and not console.confirm(question, default=False):
            return
        sql = self.DROP_USER_SQL % dict(db_user=db_user)
        self.execute_sql(sql, self.SUPERUSER)


    @task_method
    def grant_permissions(self, db_name=None, db_user=None):
        """ Grants all permissions on ``db_name`` for ``db_user``. """
        db_name, db_user, _ = self._credentials(db_name, db_user, None)

        sql = self.GRANT_PERMISSIONS_SQL % dict(db_name=db_name, db_user=db_user)
        self.execute_sql(sql, self.SUPERUSER)


    def _get_dump_filename(self, dir, db_name):
        if dir is None:
            dir = env.conf.ENV_DIR + '/var/backups'
            run('mkdir -p ' + dir)

        now = datetime.now().strftime('%Y.%m.%d-%H.%M')
        filename = '%s%s.sql' % (db_name, now)

        # if dir is absolute then PROJECT_DIR won't affect result path
        # otherwise dir will be relative to PROJECT_DIR
        return posixpath.join(env.conf.PROJECT_DIR, dir, filename)


    @task_method
    def dump(self, dir=None, db_name=None, db_user=None, db_password=None):
        """
        Dumps database.
        Result is stored at <env>/var/backups/ if dir is not provided.
        If dir is a relative path it will be relative to PROJECT_DIR.
        """
        db_name, db_user, db_password = self._credentials(db_name, db_user, db_password)
        filename = self._get_dump_filename(dir, db_name)
        return self._dump(db_user, db_password, db_name, filename)

    def _dump(self, db_user, db_password, db_name, filename):
        raise NotImplementedError()

    @task_method
    @utils.run_as_sudo
    def install(self):
        """ Installs database. """
        raise NotImplementedError()
