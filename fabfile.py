"""
ESP-Website dev server management via Fabric
"""

from fabric.api import *

from fabtools.vagrant import vagrant

import os

from fabric.contrib import files
from fabric.contrib import django as fabric_django
from fabric.context_managers import settings
from fabric.operations import get
from fabric.state import default_channel

import fabtools

from contextlib import contextmanager
import posixpath
import string
import random
import getpass
import subprocess
import socket

# Configure the Vagrant VM as the default target of our commands, so long as no
# hosts were specified on the command line. Calling `vagrant()` is sort of like
# writing `env.hosts = ['vagrant']`, but it handles the hostname and SSH config
# properly.
#
# This means that run() and sudo() will execute on the Vagrant VM by default.
#
if not env.hosts:
    try:
        vagrant()
    except SystemExit:
        print ""
        print "***** "
        print "***** Fabric encountered a fatal exception when loading the Vagrant configuration!"
        print "***** Make sure that Vagrant is running:"
        print "*****"
        print "*****   $ vagrant status"
        print "*****   $ vagrant up"
        print "***** "

        raise

fabric_django.project('esp')

REMOTE_USER = 'vagrant'
REMOTE_PROJECT_DIR = '/home/vagrant/devsite'
REMOTE_VIRTUALENV_DIR = '/home/vagrant/devsite_virtualenv'
ENCRYPTED_VG_NAME = 'ubuntu--12--vg-keep_1'

"""
The following remote_pipe() function is from:
  https://github.com/goncalopp/btrfs-send-snapshot

The code has been adapted only for style.
"""
def remote_pipe(local_command, remote_command, buf_size=1024*1024):
    """ Executes a local command and a remove command (with fabric), and
        sends the local's stdout to the remote's stdin.  """
    local_p = subprocess.Popen(local_command, shell=True, stdout=subprocess.PIPE)
    channel = default_channel()
    channel.set_combine_stderr(True)
    channel.settimeout(2)
    channel.exec_command(remote_command)
    try:
        read_bytes = local_p.stdout.read(buf_size)
        while read_bytes:
            channel.sendall(read_bytes)
            read_bytes = local_p.stdout.read(buf_size)
    except socket.error:
        local_p.kill()
        #   fail to send data, let's see the return codes and received data...
    local_ret = local_p.wait()
    received = channel.recv(buf_size)
    channel.shutdown_write()
    channel.shutdown_read()
    remote_ret = channel.recv_exit_status()
    if local_ret != 0 or remote_ret != 0:
        raise Exception("remote_pipe failed. Local retcode: {0} Remote retcode: {1} output: {2}".format(local_ret, remote_ret, received))

def relative(path):
    """ Expresses a relative path as an absolute path using `env.real_fabfile`.
        Paths are relative to the directory containing this file. """
    directory = os.path.dirname(env.real_fabfile)
    return os.path.join(directory, path)

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
    files.upload_template(relative('deploy/config_templates/local_settings.py'), '%s/esp/esp/local_settings.py' % REMOTE_PROJECT_DIR, context)

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
    fabtools.require.apache.site('devsite', template_source=relative('deploy/config_templates/apache2_vhost.conf'), **context)

def initialize_db():
    #   Activate virtualenv
    with esp_env():
        run('python manage.py migrate')
        run('python manage.py createsuperuser')

def update():
    with esp_env():
        # Trying to load a db dump with migrations ahead of your branch
        # was probably a bad idea anyway
        run('python manage.py migrate')
        run('python manage.py recompile_theme')

def link_media():
    #   Don't do this if the host is Windows (no symlinks).
    import platform
    if platform.system() == 'Windows':
        print 'Cannot link media directories on Windows.  Please copy them yourself, if this is what you want:'
        print '  cd %s' % os.path.join(os.path.dirname(__file__), 'public', 'media')
        print '  cp -r default_images images'
        print '  cp -r default_styles styles'
        return

    with cd('%s/esp/public/media' % REMOTE_PROJECT_DIR):
        with settings(warn_only=True):
            run('ln -s -T default_images images')
            run('ln -s -T default_styles styles')

def mount_encrypted_partition():
    if sudo('df | grep encrypted | wc -l').strip() == '1':
        print 'Encrypted partition is already mounted; not doing anything.'
        return
    if sudo('ls -l /dev/mapper/encrypted &> /dev/null ; echo $?').strip() != '0':
        print 'Opening the encrypted partition for data storage.'
        print 'Please enter your passphrase when prompted.'
        sudo('cryptsetup luksOpen /dev/mapper/%s encrypted' % (ENCRYPTED_VG_NAME,))
    sudo('mount /dev/mapper/encrypted /mnt/encrypted')

def unmount_encrypted_partition():
    if sudo('df | grep encrypted | wc -l').strip() == '1':
        sudo('umount /mnt/encrypted')
    if sudo('ls -l /dev/mapper/encrypted &> /dev/null ; echo $?').strip() == '0':
        sudo('cryptsetup luksClose encrypted')

def ensure_encrypted_partition():
    #   Check for the encrypted partition already existing on the
    #   VM, and quit if it does.
    if sudo('cryptsetup isLuks /dev/mapper/%s ; echo $?' % (ENCRYPTED_VG_NAME,)).strip() == '0':
        print 'Encrypted partition already exists; mounting.'
        mount_encrypted_partition()
        return
    create_encrypted_partition()

def create_encrypted_partition():
    print 'Now creating encrypted partition for data storage.'
    print 'Please make up a passphrase and enter it when prompted.'

    #   Get cryptsetup and create the encrypted filesystem
    sudo('apt-get install -y -qq cryptsetup')
    unmount_encrypted_partition()  # unmount in case it already exists
    sudo('cryptsetup luksFormat /dev/mapper/%s' % (ENCRYPTED_VG_NAME,))
    sudo('cryptsetup luksOpen /dev/mapper/%s encrypted' % (ENCRYPTED_VG_NAME,))
    sudo('mkfs.ext4 /dev/mapper/encrypted')
    sudo('mkdir -p /mnt/encrypted')
    sudo('mount /dev/mapper/encrypted /mnt/encrypted')

    #   Get postgres and create the tablespace on that filesystem
    fabtools.require.postgres.server()
    sudo('chown -R postgres /mnt/encrypted')
    run('sudo -u postgres psql -c "CREATE TABLESPACE encrypted LOCATION \'/mnt/encrypted\'"')

def load_encrypted_database(db_owner, db_filename):
    """ Load an encrypted database dump (.sql.gz.gpg) into the VM.
        Expects to receive the Postgres username of the role
        that "owns" the objects in the database (typically
        this matches the chapter's site directory name, or 'esp'
        in the case of MIT).    """

    #   Generate a new local_settings.py file with this database owner
    context = {
        'db_user': db_owner,
        'db_name': 'devsite_django',
        'db_password': gen_password(8),
        'secret_key': gen_password(64),
    }
    files.upload_template(relative('deploy/config_templates/local_settings.py'), '%s/esp/esp/local_settings.py' % REMOTE_PROJECT_DIR, context)

    #   Set up the user (with blank DB) in Postgres
    run('sudo -u postgres psql -c "DROP DATABASE IF EXISTS devsite_django"')
    run('sudo -u postgres psql -c "DROP ROLE IF EXISTS %s"' % (db_owner,))
    run('sudo -u postgres psql -c "CREATE ROLE %s CREATEDB LOGIN PASSWORD \'%s\'"' % (db_owner, context['db_password']))
    run('sudo -u postgres psql -c "CREATE DATABASE devsite_django OWNER %s TABLESPACE encrypted"' % (db_owner,))

    #   Decrypt the DB dump (if needed) and send to the VM's Postgres install.
    #   This sends the SQL commands to the VM via the remote_pipe function.
    if db_filename.endswith('.gpg'):
        local_cmd = 'gpg -d %s | gunzip -c' % (db_filename,)
    else:
        local_cmd = 'gunzip -c %s' % (db_filename,)
    remote_cmd = 'sudo -u postgres psql devsite_django'
    remote_pipe(local_cmd, remote_cmd)

@task
def load_db_dump(dbuser, dbfile):
    """ Create an encrypted partition on the VM and load a database dump
        using that encrypted storage.   """

    ensure_encrypted_partition()
    load_encrypted_database(dbuser, dbfile)
    update()

@task
def recreate_encrypted_partition():
    """ Blow away any previous encrypted partition and create a new one. """

    create_encrypted_partition()

@task
def vagrant_dev_setup(dbuser=None, dbfile=None):
    """ Set up the development environment.
        If the dbuser and dbfile arguments are supplied, sets up
        encrypted database storage and loads a DB dump. """

    if dbuser is not None and dbfile is None:
        raise Exception('You must provide a database dump file to load in the dbfile argument.')
    if dbuser is None and dbfile is not None:
        raise Exception('You must specify the PostgreSQL user that your database belongs to in the dbuser argument.')
    using_db_dump = (dbuser is not None and dbfile is not None)

    if using_db_dump:
        load_db_dump(dbuser, dbfile)
    else:
        create_settings()
        initialize_db()
    setup_apache()
    link_media()

@task
def run_devserver():
    """ Run Django dev server on port 8000. """
    with esp_env():
        sudo('python manage.py runserver 0.0.0.0:8000')

@task
def manage(cmd):
    """ Run a manage.py command """
    with esp_env():
        sudo('python manage.py '+cmd)

@task
def update_deps():
    with esp_env():
        sudo('python manage.py update_deps')

@task
def open_db():
    """ Mounts the encrypted filesystem containing any loaded database
        dumps.  Should be executed after 'vagrant up' and before any
        other operations such as run_devserver. """
    mount_encrypted_partition()

@task
def reload_apache():
    """ Reload apache2 server. """
    sudo('service apache2 reload')
