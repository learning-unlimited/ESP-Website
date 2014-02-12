# coding: utf-8
from __future__ import with_statement

from fabric.api import run, env, hide, settings, sudo, puts
from taskset import task_method

from fab_deploy import utils
from fab_deploy import system
from fab_deploy.db import base


class Postgres(base.Database):
    name = 'PostgeSQL'

    SUPERUSER = 'postgres'

    CREATE_USER_SQL = "CREATE USER %(db_user)s WITH PASSWORD '%(db_password)s' CREATEDB;"
    CREATE_DB_SQL = "CREATE DATABASE %(db_name)s OWNER %(db_user)s ENCODING 'UTF8' TEMPLATE %(template)s;"
    USER_EXISTS_SQL = "SELECT 1 FROM pg_roles WHERE rolname='%(db_user)s';"
    GRANT_PERMISSIONS_SQL = "GRANT ALL PRIVILEGES ON DATABASE %(db_name)s TO '%(db_user)s';"

    @task_method
    def is_installed(self):
        with settings(hide('running', 'stdout', 'stderr', 'warnings'), warn_only=True):
            output = run('psql --version')
        return output.succeeded

    @task_method
    @utils.run_as_sudo
    def install(self):
        """ Installs postgresql. """
        packages = 'postgresql-server-dev-all postgresql'
        system.aptitude_install(packages)
        self.create_db()

    @task_method
    def execute_sql(self, sql, user=None, password=None, db_name=None):
        db_user = user or env.conf.DB_USER
        #db_host = env.conf.DB_HOST
        if password is None and db_user != self.SUPERUSER:
            password = env.conf.DB_PASSWORD

        sql = sql.replace('"', r'\"')

        # TODO: superuser password auth?
        if db_user == self.SUPERUSER:
            cmd = 'psql --command "%s"' % sql
            @utils.run_as_sudo
            def sudo_cmd():
                return sudo(cmd, user=db_user, quiet=True)
            return sudo_cmd()

        pwd_cmd = "export PGPASSWORD='%s';" % password if password is not None else ''

        # TODO: configurable DB_HOST
        # we have to set host because password auth is off for sockets by default
        db_name = db_name or env.conf.DB_NAME
        cmd = 'psql %s --user="%s" --host=127.0.0.1 --command "%s"' % (db_name, db_user, sql,)
        return run(pwd_cmd + cmd, pty=False, combine_stderr=False, shell=False, quiet=True)

    @task_method
    def _user_exists(self, db_user):
        sql = self.USER_EXISTS_SQL % dict(db_user=db_user)
        with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
            result = self.execute_sql(sql, self.SUPERUSER)
        return '1' in result

    @task_method
    @utils.run_as_sudo
    def _db_exists(self, db_name):
        # XXX: this is untested
        cmd = 'psql -ltA | grep -q "^%s|"' % db_name
        return sudo(cmd, user=self.SUPERUSER).succeeded

    @task_method
    @utils.run_as('postgres')
    def create_db(self, db_name=None, db_user=None, root_password=None, template='template1'):
        """ Creates an empty PostgreSQL database. """

        if db_user != self.SUPERUSER:
            self.create_user(db_user=db_user)

        db_name, db_user, _ = self._credentials(db_name, db_user, None)

        sql = self.CREATE_DB_SQL % dict(db_name=db_name, db_user=db_user, template=template)
        self.execute_sql(sql, self.SUPERUSER, root_password)
        self.grant_permissions(db_name=db_name, db_user=db_user)


    def _dump(self, db_user, db_password, db_name, filename):
        cmd = 'PGPASSWORD="%(db_password)s" pg_dump --username="%(db_user)s" %(db_name)s | gzip -3 > %(filename)s.gz' % dict(
            db_password = db_password,
            db_user = db_user,
            db_name = db_name,
            filename = filename
        )
        run(cmd)


instance = Postgres()
__all__ = instance.expose_to_current_module()

#def deploy_postgres():
#    postgres_install()
#    postgres_create_user()
#    postgres_create_postgis_db()
#
