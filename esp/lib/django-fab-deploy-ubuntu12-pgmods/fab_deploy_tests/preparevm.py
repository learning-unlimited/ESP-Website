#!/usr/bin/env python
import sys
import os

# always use fab_deploy from the checkout, not the installed version
# plus make fab_deploy_tests available for imports
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, path)

from fabric.api import env, sudo, run
from fabtest import fab, VirtualBox

from fab_deploy.utils import update_env
from fab_deploy.system import prepare
from fab_deploy.db import mysql, postgres
from fab_deploy.webserver.nginx import Nginx
from fab_deploy.webserver.apache import Apache

from utils import setup_ssh, setup_sudo, private_key_path

def _download_pip_requirements():
    DIR = '/tmp/sdist'
    run('mkdir -p %s' % DIR)
    reqs = [
        'django == 1.2.5',
        'django == 1.4',
        'mysql-python == 1.2.3',
        'psycopg2 == 2.4.5',
        'South == 0.7.5',
        'port-for == 0.3',
    ]
    for req in reqs:
        run("pip install -d %s '%s'" % (DIR, req))

    run('chmod 0777 -R %s' % DIR)


def deep_prepare(name):
    """ Deep VM preparation for test speedups.
    Should only be run if all related tests are passed.

    It now prepares an extra snapshot with basic software,
    apache, nginx, mysql and postgres installed.

    VM is not executed in headless mode because snapshot taking
    seems to be broken in this mode.
    """
    env.hosts = ['foo@127.0.0.1:2222']
    env.password = '123'
    env.disable_known_hosts = True
    env.conf = {'DB_PASSWORD': '123', 'DB_USER': 'root', 'DB_BACKEND': 'mysql'}
    env.key_filename = private_key_path()
    update_env()

    box = VirtualBox(name)

    if not box.snapshot_exists('fabtest-prepared-server'):
        box.snapshot_restore('fabtest-initial')
        setup_sudo()
        setup_ssh()
        fab(prepare)
        fab(Apache().install, confirm=False)
        fab(Nginx().install)
        fab(mysql.install)
        fab(postgres.install)
        fab(_download_pip_requirements)
        box.snapshot_take('fabtest-prepared-server')

    box.stop()


if __name__ == '__main__':
    deep_prepare(sys.argv[1])

