""" Quick commands for managing a development environment """

#
# Warning to fabfile developers.
#
# This file is executed by Fabric on the developer's host machine. Host machines
# may run Windows, Mac OS or Linux and may not have all of the esp-website
# dependencies installed. Therefore:
#
#   - Take care when importing Python modules in this file. The only modules we
#     know are present come from the standard library, Fabric, and fabtools.
#
#   - Take care when using local() to run commands locally. Make sure to
#     construct local paths using os.path.join() (here imported as join()), and
#     do not assume the presence of Unix utilies like find and sed.
#
#     In addition, use env.lbase to construct absolute paths when referring to
#     local files, since fab may be invoked from anywhere in the source tree.
#

from fabric.api import *
from fabric.contrib import files

import os
import pipes
import platform

from os.path import join

# Remote base directory, with trailing /
env.rbase = "/home/vagrant/devsite/"

# Remote virtualenv directory, with trailing /
env.venv = "/home/vagrant/venv/"

# Local base directory
env.lbase = os.path.dirname(env.real_fabfile)

# Name of the encrypted volume group in the Vagrant VM
env.encvg = "ubuntu--12--vg-keep_1"

# Configure the Vagrant VM as the default target of our commands, so long as no
# hosts were specified on the command line. Calling vagrant() is sort of like
# writing env.hosts = ["vagrant"], but it handles the hostname and SSH config
# properly.
#
# This means that run() and sudo() will execute on the Vagrant VM by default.
#
if not env.hosts:
    try:
        from fabtools.vagrant import vagrant
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

@task
def setup():
    """
    Perform initial configuration of a brand-new VM. May fail if run again.
    """
    update_deps()

    # Create and mount the encrypted partition (requires user input)
    from fabtools import require
    require.deb.package("cryptsetup")
    sudo("cryptsetup luksFormat /dev/mapper/%s" % env.encvg)
    sudo("cryptsetup luksOpen /dev/mapper/%s encrypted" % env.encvg)
    sudo("mkfs.ext4 /dev/mapper/encrypted")
    sudo("mkdir -p /mnt/encrypted")
    sudo("mount /dev/mapper/encrypted /mnt/encrypted")

    # Create the encrypted tablegroup in Postgres
    sudo("chown -R postgres /mnt/encrypted")
    psql("CREATE TABLESPACE encrypted LOCATION '/mnt/encrypted'")

    # Automatically activate virtualenv
    files.append("~/.bash_login", "source %sbin/activate" % env.venv)

    # Symlink media
    if platform.system() == "Windows":
        # Creating symlinks inside the guest will fail if the host is running
        # Windows. We need to create the symlinks on the host, which requires
        # administrator privileges. This script takes care of the whole process.
        local(join(env.lbase, "deploy", "windows_symlink_media.bat"))
    else:
        with cd(env.rbase + "esp/public/media"):
            with settings(warn_only=True):
                run("ln -s -T default_images images")
                run("ln -s -T default_styles styles")

    sudo("touch /fab-setup-done")

def update_deps():
    """
    Run update_deps.sh to:
      - install Ubuntu packages
      - configure a virtualenv
      - install Python packages

    This script should be safe to run multiple times. It will use sudo to gain
    elevated permissions as needed, so we can use run() here instead of sudo().
    """
    run(env.rbase + "esp/update_deps.sh --virtualenv=" + env.venv)

@task
def psql(cmd=None, *args):
    """
    Run the given Postgres command as user postgres. If no command is
    specified, open an interactive psql shell.

    When called from Python code, performs string interpolation on the command
    with the subsequent arguments.
    """
    ensure_environment()
    if cmd:
        sudo("psql -c " + pipes.quote(cmd % args), user="postgres")
    else:
        open_shell("sudo -u postgres psql; exit")

@runs_once
def ensure_environment():
    """
    Ensure that the environment is fully configured. If so, print no output and
    return. If not, attempt to fix the problem (e.g. some things need to be done
    every time the VM boots) or else print instructions and terminate fab.

    For efficiency, the result of this function is cached for the duration of a
    run of fab. We assume that an already-configured environment will not become
    un-configured.
    """
    # Has setup() been run?
    if not files.exists("/fab-setup-done"):
        print ""
        print "***** "
        print "***** The Vagrant VM has not been configured. Please run:"
        print "***** "
        print "*****   $ fab setup"
        print "***** "
        exit(-1)

    # Ensure that the encrypted partition has been mounted (must be done after
    # every boot, and can't be done automatically by Vagrant :/)
    if sudo("df | grep encrypted | wc -l").strip() != "1":
        if sudo("ls -l /dev/mapper/encrypted &> /dev/null ; echo $?").strip() != "0":
            print "***** "
            print "***** Opening the encrypted partition for data storage."
            print "***** Please enter your passphrase when prompted."
            print "***** "
            sudo("cryptsetup luksOpen /dev/mapper/%s encrypted" % env.encvg)
            sudo("mount /dev/mapper/encrypted /mnt/encrypted")
        else:
            print "***** "
            print "***** Something went wrong when mounting the encrypted partition."
            print "***** Aborting."
            exit(-1)
