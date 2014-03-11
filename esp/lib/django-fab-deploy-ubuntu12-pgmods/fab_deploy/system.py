# coding: utf-8
from __future__ import with_statement
import os.path

from fabric.api import run, settings, env, cd, sudo, task
from fabric.contrib import files
from fabric import utils as fabric_utils

from fab_deploy import utils

__all__ = ['create_linux_account', 'create_sudo_linux_account',
           'ssh_add_key', 'ssh_add_root_key', 'install_sudo']

@task
def prepare():
    """ Prepares server: installs system packages. """
    os = utils.detect_os()
    if os in ['lenny', 'squeeze']:
        install_sudo()

    setup_backports()
    install_software()

@task
@utils.run_as('root')
def install_sudo():
    """ Installs sudo on server. """
    _aptitude_update_using(run)
    run('aptitude install -y sudo')

@task
@utils.run_as_sudo
def install_software():
    """ Installs common system packages. """
    common_packages = [
        'python', 'build-essential', 'python-dev', 'python-setuptools',
        'python-profiler', 'libjpeg-dev', 'zlib1g-dev',
        'libssl-dev', 'libcurl3-dev',
        'libxml2-dev', 'libxslt1-dev', # for lxml
	'memcached',
        'subversion',
    ]
    aptitude_install(" ".join(common_packages))

    # git and mercurial are outdated in stable Debian Lenny and
    # don't work with some source repositories on github and bitbucket
    vcs_options = {'lenny': '-t lenny-backports'}
    aptitude_install('mercurial git git-core', vcs_options.get(os, ""))
    aptitude_install('bzr', '--without-recommends')

    sudo('easy_install -U pip')
    sudo('pip install -U virtualenv')
    sudo('pip install port-for==0.3')

@task
@utils.run_as_sudo
def setup_backports():
    """ Adds backports repo to apt sources. """
    os = utils.detect_os()
    backports = {
        'lenny': 'http://backports.debian.org/debian-backports lenny-backports main contrib non-free',
        'squeeze': 'http://backports.debian.org/debian-backports squeeze-backports main contrib non-free',
        'maverick': 'http://archive.ubuntu.com/ubuntu maverick-backports main universe multiverse restricted',
        'lucid': 'http://archive.ubuntu.com/ubuntu lucid-backports main universe multiverse restricted',
        'precise': 'http://archive.ubuntu.com/ubuntu precise-backports main universe multiverse restricted',
    }

    if os not in backports:
        fabric_utils.puts("Backports are not available for " + os)
        return

    sudo("echo 'deb %s' > /etc/apt/sources.list.d/backports.sources.list" % backports[os])
    with settings(warn_only=True):
        sudo('aptitude update')
        env.conf._APTITUDE_UPDATED = True

@task
@utils.run_as_sudo
def create_linux_account(pub_key_file, username=None):
    """
    Creates linux account, setups ssh access and pip.conf file.

    Example::

        fab create_linux_account:"/home/kmike/.ssh/id_rsa.pub"

    """
    with open(os.path.normpath(pub_key_file), 'rt') as f:
        ssh_key = f.read()

    username = username or env.conf.USER

    with (settings(warn_only=True)):
        sudo('adduser %s --disabled-password --gecos ""' % username)

    home_dir = utils.get_home_dir(username)
    with cd(home_dir):
        sudo('mkdir -p .ssh')
        files.append('.ssh/authorized_keys', ssh_key, use_sudo=True)
        sudo('chown -R %s:%s .ssh' % (username, username))

    # workaround for circular import
    # FIXME: there shouldn't be circular imports
    from fab_deploy import pip
    pip.setup_conf(username=username)

@task
@utils.run_as('root')
def create_sudo_linux_account(pub_key_file, username=None):
    """ Creates linux account, setups ssh access and
    adds the created user to sudoers. This command requires root ssh access. """
    username = username or env.conf.SUDO_USER
    if username == 'root':
        return

    home_dir = '/home/%s' % username

    with open(os.path.normpath(pub_key_file), 'rt') as f:
        ssh_key = f.read()

    with (settings(warn_only=True)):
        run('adduser %s --disabled-password --gecos ""' % username)
        with cd(home_dir):
            run('mkdir -p .ssh')
            files.append('.ssh/authorized_keys', ssh_key)
            run('chown -R %s:%s .ssh' % (username, username))

    line = '%s ALL=(ALL) NOPASSWD: ALL' % username
    files.append('/etc/sudoers', line)

@task
def ssh_add_key(pub_key_file):
    """ Adds a ssh key from passed file to user's authorized_keys on server. """
    with open(os.path.normpath(pub_key_file), 'rt') as f:
        ssh_key = f.read()
    run('mkdir -p .ssh')
    files.append('.ssh/authorized_keys', ssh_key)

@task
@utils.run_as('root')
def ssh_add_root_key(pub_key_file):
    """ Adds a ssh key from passed file to root's authorized_keys on server. """
    return ssh_add_key(pub_key_file)

@task
@utils.run_as_sudo
def aptitude_install(packages, options=''):
    """ Installs package via aptitude. """
    _aptitude_update_using(sudo)
    sudo('aptitude install %s -y %s' % (options, packages,))


def _aptitude_update_using(cmd):
    if not hasattr(env.conf, '_APTITUDE_UPDATED'):
        cmd('aptitude update')
        env.conf._APTITUDE_UPDATED = True


#@utils.run_as_sudo
#def install_backup_system():
#    sudo('aptitude install -y s3cmd ruby rubygems libxml2-dev libxslt-dev libopenssl-ruby')
#    sudo('gem install rubygems-update')
#    sudo('/var/lib/gems/1.8/bin/update_rubygems')
#    sudo('gem install astrails-safe --source http://gemcutter.org')
