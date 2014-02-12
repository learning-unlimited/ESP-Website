# -*- coding: utf-8 -*-
from __future__ import absolute_import
from fabric.api import env
from fabtest import fab
from fab_deploy.db import postgres
from ..utils import setup_sudo
from .base import FabDeployTest

def postgres_is_installed():
    return fab(postgres.is_installed)

def database_exists(db_name):
    user_name = postgres.Postgres.SUPERUSER
    databases = fab(postgres.execute_sql, 'select datname from pg_database;', user_name)
    return db_name in databases

class PostgresInstallTest(FabDeployTest):
    host = 'root@127.0.0.1:2222'

    def setup_conf(self):
        super(PostgresInstallTest, self).setup_conf()
        env.conf['DB_PASSWORD'] = '123'
        env.conf['DB_NAME'] = 'new_database'
        env.conf['DB_USER'] = 'vasia'

    def test_install(self):
        setup_sudo()
        self.assertFalse(postgres_is_installed())
        fab(postgres.install)
        self.assertTrue(postgres_is_installed())


class PostgresSetupTest(FabDeployTest):
    host = 'root@127.0.0.1:2222'
    snapshot = 'fabtest-prepared-server'

    def setup_conf(self):
        super(PostgresSetupTest, self).setup_conf()
        env.conf['DB_PASSWORD'] = '123'
        env.conf['DB_NAME'] = 'new_database'
        env.conf['DB_USER'] = 'vasia'

    def test_postgres(self):
        self.assertTrue(postgres_is_installed())

        self.assertFalse(database_exists('new_database'))
        fab(postgres.create_user)
        fab(postgres.create_db)
        self.assertTrue(database_exists('new_database'))

        # create table
        fab(postgres.execute_sql, "create table baz (id int);")

        # check if it is created
        test_sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        output = fab(postgres.execute_sql, test_sql)
        tables = output.splitlines()[1:]
        self.assertEqual(tables[1].strip(), 'baz')
