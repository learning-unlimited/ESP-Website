# coding: utf-8
from __future__ import with_statement

from fabric.api import env, run, warn, abort
from fabric.context_managers import settings, hide
from fabric.operations import sudo
from fabric.utils import puts
from taskset import task_method

from fab_deploy import utils
from fab_deploy import system
from fab_deploy.db import base

class Mysql(base.Database):
    name = 'MySQL'

    CREATE_USER_SQL = """CREATE USER '%(db_user)s'@'localhost' IDENTIFIED BY '%(db_password)s';"""
    DROP_USER_SQL = "DROP USER %(db_user)s;"
    CREATE_DB_SQL = """CREATE DATABASE %(db_name)s DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;"""
    GRANT_PERMISSIONS_SQL = """
    GRANT ALL ON %(db_name)s.* TO '%(db_user)s'@'localhost';
    FLUSH PRIVILEGES;
    """
    USER_EXISTS_SQL = "SHOW GRANTS FOR '%(db_user)s'@localhost"

    mysql_versions = {
        'lenny': '5.0',
        'squeeze': '5.1',
        'lucid': '5.1',
        'maverick': '5.1',
    }

    def _get_version(self):
        os = utils.detect_os()
        return self.mysql_versions[os]

    @utils.run_as_sudo
    def _preseed_password(self, passwd):
        version = self._get_version()
        # this way mysql won't ask for a password on installation
        # see http://serverfault.com/questions/19367/scripted-install-of-mysql-on-ubuntu
        system.aptitude_install('debconf-utils')

        debconf_defaults = [
            "mysql-server-%s mysql-server/root_password_again password %s" % (version, passwd),
            "mysql-server-%s mysql-server/root_password password %s" % (version, passwd),
        ]

        sudo("echo '%s' | debconf-set-selections" % "\n".join(debconf_defaults))

        warn('\n=========\nThe password for mysql "root" user will be set to "%s"\n=========\n' % passwd)


    @task_method
    @utils.run_as_sudo
    def install(self):
        """ Installs mysql. """
        if self.is_installed():
            puts('Mysql is already installed.')
            return
        extra_packages = {
            'lenny': ['libmysqlclient15-dev'],
            'squeeze': ['libmysqlclient-dev'],
            'maverick': ['libmysqlclient-dev'],
            'lucid': ['libmysqlclient-dev'],
        }
        os = utils.detect_os()
        if os not in extra_packages:
            abort('Your OS (%s) is unsupported now.' % os)
        passwd = self._get_root_password()
        self._preseed_password(passwd)

        system.aptitude_install('mysql-server')
        system.aptitude_install(' '.join(extra_packages[os]))

    @task_method
    def is_installed(self):
        with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
            output = run('mysql --version')
        return output.succeeded


    def _dump(self, db_user, db_password, db_name, filename):
        run('mysqldump --user="%s" --password="%s" %s > %s' % (
                            db_user, db_password, db_name, filename))

    def _credentials_for_sql(self, user, password):
        # XXX: why _credentials and _credentials_for_sql are different?
        user = user or env.conf.DB_USER
        if user == self.SUPERUSER and password is None:
            password = self._get_root_password()
        elif password is None:
            password = env.conf.DB_PASSWORD
        return user, password

    @task_method
    def execute_sql(self, sql, user=None, password=None, db_name=None):
        """ Executes passed sql command using mysql shell. """
        user, password = self._credentials_for_sql(user, password)
        sql = sql.replace('"', r'\"')

        if user != self.SUPERUSER:
            db_name = db_name or env.conf.DB_NAME
        else:
            db_name = '' # do not select database for superuser

        return run('echo "%s" | mysql --user="%s" --password="%s" %s' % (sql, user , password, db_name))

instance = Mysql()
__all__ = instance.expose_to_current_module()