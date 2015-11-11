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

import json
import os
import pipes
import platform
import random
import string

from os.path import join

# Remote base directory, with trailing /
env.rbase = "/home/vagrant/devsite/"

# Remote virtualenv directory, with trailing /
env.venv = "/home/vagrant/venv/"

# Local base directory
env.lbase = os.path.dirname(env.real_fabfile)

# Name of the encrypted volume group in the Vagrant VM
env.encvg = "ubuntu--12--vg-keep_1"

# Name of the Postgres database
env.dbname = "devsite_django"

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

@task
def emptydb(owner="esp"):
    """
    Delete any existing Postgres database and replace it with an empty one.

    This task additionally rotates the database credentials and regenerates
    local_settings.py.
    """
    ensure_environment()

    # Generate a new local_settings.py file with this database owner
    password = gen_password(12)
    context = {
        "db_user": owner,
        "db_name": env.dbname,
        "db_password": password,
        "secret_key": gen_password(64),
    }
    files.upload_template(
        join(env.lbase, "deploy", "config_templates", "local_settings.py"),
        env.rbase + "esp/esp/local_settings.py",
        context,
        backup=False,
    )

    # Delete and recreate the Postgres user and database. Note that the PASSWORD
    # command requires single-quotes, not double-quotes as is usual.
    psql("DROP DATABASE IF EXISTS %s", env.dbname)
    psql("DROP ROLE IF EXISTS %s", owner)

    psql("CREATE ROLE %s CREATEDB LOGIN PASSWORD '" + password + "'", owner)
    psql("CREATE DATABASE %s OWNER %s TABLESPACE encrypted", env.dbname, owner)

@task
def loaddb(filename=None):
    """
    If filename is given, load the (decrypted, uncompressed) database dump at
    that local path into the Postgres database.

    If filename is not given, download the dump over HTTP, prompting the user
    for the URL if one has not been previously provided.

    Automatically detects the dump format and proper username.
    """
    ensure_environment()

    # Clean up existing dumpfile, if present
    run("rm -f ~/dbdump")

    if filename:
        put(filename, "~/dbdump")
    else:
        # Get or prompt for HTTP download settings. These settings are saved in
        # ~/.dbdownload in the Vagrant VM, which makes it easier for people to
        # work with different chapters' databasees in different VMs.
        if files.exists("~/.dbdownload"):
            contents = run("cat ~/.dbdownload")
            config = json.loads(contents)
        else:
            url = prompt("Download URL:")
            config = {
                "url": url,
            }
            escaped_config = pipes.quote(json.dumps(config))
            run("echo " + escaped_config + " > ~/.dbdownload")

        # Download database dump into VM
        escaped_url = pipes.quote(config["url"])
        run("wget " + escaped_url + " -O ~/dbdump")

    # HACK: detect the Postgres user used in the dump. We run strings in case
    # the dump is in binary format, then we look for the grant for arbitrary
    # table, program_class. The result should be a line like:
    #
    #   GRANT ALL ON TABLE program_clas TO esp;
    #
    # ...which we can then parse to get the user. :D
    contents = run("strings dbdump | grep 'GRANT ALL ON TABLE program_class TO'")
    pg_owner = contents.split()[-1][:-1]

    # Reset the database
    emptydb(pg_owner)

    # Load the database dump (pg_restore autodetects the dump format)
    sudo("chgrp postgres ~/dbdump")
    sudo("pg_restore --verbose --dbname=" + pipes.quote(env.dbname) +
         " --exit-on-error --jobs=2 ~/dbdump",
         user="postgres")

    # Cleanup
    run("rm -f ~/dbdump")

def gen_password(length):
    return "".join([random.choice(string.letters + string.digits) for i in range(length)])

@task
def manage(cmd):
    """
    Run a manage.py command in the remote host.
    """
    ensure_environment()

    if cmd in ["shell", "shell_plus"]:
        # cd() doesn't work with open_shell
        open_shell("(cd " + env.rbase + "esp && python manage.py " + cmd + "); exit")
    else:
        with cd(env.rbase + "esp"):
            run("python manage.py " + cmd)

@task
def runserver():
    """
    A shortcut for 'manage.py runserver' with the appropriate settings.
    """
    ensure_environment()

    manage("runserver 0.0.0.0:8000")

@task
def refresh():
    """
    Re-synchronize the remote environment with the codebase. For use when
    switching branches or jumping around the history in git.

      - upgrades and downgrades Python packages
      - removes orphaned *.pyc files
      - runs Django database migrations
    """
    ensure_environment()

    with cd(env.rbase):
        # Update the virtualenv with correct packages
        run("pip install --upgrade -r " + env.rbase + "esp/requirements.txt")

        # Clean up *.pyc files that contain stale code. In practice, the only
        # files that cause problems are orphaned *.pyc's where the corresponding
        # *.py file has been deleted (git leaves the *.pyc in place). Other than
        # this, *.pyc files cannot be stale because git updates the lastmod time
        # when changing a file, so a freshly checked out *.py file will always
        # be newer than its *.pyc, triggering a recompile. This is an optimization
        # over 'manage.py clean_pyc', which deletes all *pyc's in the source
        # tree.. Note that this command is run in the Vagrant VM, since the host
        # may not have find installed.
        run("""find . -name '*.pyc' -exec bash -c 'test ! -f "${1%c}"' -- {} \; -delete""")

        # Run Django migrations
        manage("migrate")

        # Recompile theme (run twice, to work around bug)
        manage("recompile_theme")
        manage("recompile_theme")
