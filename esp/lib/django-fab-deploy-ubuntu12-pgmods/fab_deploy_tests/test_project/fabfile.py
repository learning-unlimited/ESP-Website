from fabric.api import env, task

from fab_deploy.utils import define_host, update_env
from fab_deploy.project import WebProject

project = WebProject().expose_as_module('project')

@define_host('foo@127.0.0.1:2222')
def foo_site():
    return dict(
        DB_USER = 'root',
        DB_PASSWORD = '123',
        DB_BACKEND = 'dummy',
        VCS = 'none',
        SERVER_NAME = 'foo.example.com'
    )

@task
def bar_site():
    env.hosts = ['foo@127.0.0.1:2222']
    env.conf = dict(
        DB_USER = 'root',
        DB_PASSWORD = '123',
        DB_BACKEND = 'dummy',
        VCS = 'none',
        SERVER_NAME = 'bar.example.com',
        INSTANCE_NAME = 'bar',
    )
    update_env()

@define_host('foo@127.0.0.1:2222')
def invalid_site():
    return dict(
        DB_USER = 'root',
        DB_PASSWORD = '123',
        DB_BACKEND = 'dummy',
        VCS = 'none',
        SERVER_NAME = 'invalid.example.com',
        INSTANCE_NAME = 'invalid',
        EXTRA = 'raise Exception()',
    )
