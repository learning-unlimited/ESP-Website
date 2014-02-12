# coding: utf-8
from __future__ import absolute_import
from taskset import task_method
from .base import Database

__all__ = ['Dummy']

class Dummy(Database):
    name = 'Dummy'

    @task_method
    def is_installed(self):
        return True

    @task_method
    def execute_sql(self, sql, user=None, password=None):
        pass

    @task_method
    def _user_exists(self, db_user):
        return False

    @task_method
    def create_user(self, db_user=None, db_password=None):
        pass

    @task_method
    def create_db(self, db_name=None, db_user=None, root_password=None):
        pass

    @task_method
    def drop_db(self, db_name, confirm=True):
        pass

    @task_method
    def grant_permissions(self, db_name=None, db_user=None):
        pass

    @task_method
    def dump(self, dir=None, db_name=None, db_user=None, db_password=None):
        pass

    @task_method
    def install(self):
        pass

instance = Dummy()
# do not expose tasks for command-line usage because they are not useful