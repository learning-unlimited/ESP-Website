"""
ESP-Website dev server management via Fabric
"""

from fabric.api import env, local, run, task, cd, prefix, sudo
from fabric.contrib import files
from fabric.contrib import django as fabric_django
from fabric.context_managers import settings
from fabric.operations import get

import fabtools
import fabtools.vagrant

from contextlib import contextmanager
import posixpath
import string
import random

fabric_django.project('esp')

REMOTE_USER = 'vagrant'
REMOTE_PROJECT_DIR = '/home/vagrant/devsite'
REMOTE_VIRTUALENV_DIR = '/home/vagrant/devsite_virtualenv'

def use_vagrant():
    vagrant_key_file = local('cd ../vagrant && vagrant ssh-config | grep IdentityFile', capture=True).split(' ')[1]
    host_str = '127.0.0.1:2222'
    config_dict = {
        'user': REMOTE_USER,
        'hosts': [host_str],
        'host_string': host_str,
        'key_filename': vagrant_key_file,
    }
    return settings(**config_dict)

@contextmanager
def esp_env():
    with cd('%s/esp' % REMOTE_PROJECT_DIR):
        with prefix('source %s/bin/activate' % REMOTE_VIRTUALENV_DIR):
            yield

def gen_password(length):
    return ''.join([random.choice(string.letters + string.digits) for i in range(length)])

def create_settings():
    context = {
        'db_user': 'ludev',
        'db_name': 'devsite_django',
        'db_password': gen_password(8),
        'secret_key': gen_password(64),
    }
    
    #   Initialize the database as specified in the settings
    fabtools.require.postgres.server()
    fabtools.require.postgres.user(context['db_user'], context['db_password'])
    fabtools.require.postgres.database(context['db_name'], context['db_user'])

    #   Create the local_settings.py file on the target
    files.upload_template('./config_templates/local_settings.py', '%s/esp/esp/local_settings.py' % REMOTE_PROJECT_DIR, context)

def setup_apache():
    context = {
        'APACHE_PORT': 80,
        'SERVER_NAME': 'devsite.learningu.org',
        'SERVER_ADMIN': 'devsite@learningu.org',
        'INSTANCE_NAME': 'devsite',
        'USER': REMOTE_USER,
        'PROCESSES': '1',
        'THREADS': '1',
        'PROJECT_DIR': REMOTE_PROJECT_DIR,
    }

    #   Note: Apache2 isn't installed for base config (but we don't want all of the
    #   production stuff); fabtools provides a convenient interface
    fabtools.require.apache.server()
    fabtools.require.deb.package('libapache2-mod-wsgi')
    fabtools.require.apache.module_enabled('wsgi')
    fabtools.require.apache.site_disabled('default')
    fabtools.require.apache.site('devsite', template_source='./config_templates/apache2_vhost.conf', **context)

def initialize_db():
    #   Activate virtualenv (should make a context manager)
    with esp_env():
        run('python manage.py syncdb')
        run('python manage.py migrate')

def link_media():
    #   Don't do this if the host is Windows (no symlinks).
    import platform
    if platform.system() == 'Windows':
        import os
        print 'Cannot link media directories on Windows.  Please copy them yourself, if this is what you want:'
        print '  cd %s' % os.path.join(os.path.dirname(__file__), 'public', 'media')
        print '  cp -r default_images images'
        print '  cp -r default_styles styles'
        return

    with cd('%s/esp/public/media' % REMOTE_PROJECT_DIR):
        run('ln -s default_images images')
        run('ln -s default_styles styles')

@task
def vagrant_dev_setup():
    """ Set up the development environment. """
    with use_vagrant():
        create_settings()
        setup_apache()
        link_media()
        initialize_db()

@task
def run_devserver():
    """ Run Django dev server on port 8000. """
    with use_vagrant():
        with esp_env():
            sudo('python manage.py runserver 0.0.0.0:8000')

@task
def reload_apache():
    """ Reload apache2 server. """
    with use_vagrant():
        sudo('service apache2 reload')
