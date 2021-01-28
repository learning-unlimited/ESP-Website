""" Quick commands for managing an ESP website development environment """

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
import sys

from os.path import join

# Remote base directory, with trailing /
env.rbase = "/home/vagrant/devsite/"

# Remote virtualenv directory, with trailing /
env.venv = "/home/vagrant/venv/"

# Local base directory, e.g. C:\Users\Tim\ESP-Website
env.lbase = os.path.dirname(env.real_fabfile)

# Name of the encrypted volume group in the Vagrant VM
env.encvg = "vgvagrant-keep_1"

# Name of the Postgres database
env.dbname = "devsite_django"

# Location where Fabric can store db-related files, with trailing /
env.encfab = "/mnt/encrypted/fabric/"

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
    env.setup_running = True

    # Install Ubuntu packages, create a virtualenv and install Python packages.
    # The script uses sudo to elevate as needed, so we can use run() here
    # instead of sudo().
    run(env.rbase + "esp/update_deps.sh --virtualenv=" + env.venv)

    # Create and mount the encrypted partition (requires user input)
    from fabtools import require
    require.deb.package("cryptsetup")

    print "***** "
    print "***** Creating the encrypted partition for data storage."
    print "***** Please choose a passphrase and type it at the prompts."
    print "***** "

    sudo("cryptsetup luksFormat -q /dev/mapper/%s" % env.encvg)
    sudo("cryptsetup luksOpen /dev/mapper/%s encrypted" % env.encvg)
    sudo("mkfs.ext4 /dev/mapper/encrypted")
    sudo("mkdir -p /mnt/encrypted")
    sudo("mount /dev/mapper/encrypted /mnt/encrypted")

    # Create the encrypted tablegroup in Postgres
    sudo("chown -R postgres /mnt/encrypted")
    psql("CREATE TABLESPACE encrypted LOCATION '/mnt/encrypted'")

    # Create a directory on the encrypted partition for miscellaneous storage
    # and make it accessible to everyone (e.g. both vagrant and postgres need to
    # access the database dump).
    sudo("chmod +rx /mnt/encrypted")
    sudo("mkdir " + env.encfab)
    sudo("chmod a+rwx " + env.encfab)

    # Automatically activate virtualenv. We rely on this so that we don't have
    # to activate the virtualenv as part of every fab command.
    files.append("~/.bash_login", "source %sbin/activate" % env.venv)

    # Configure memcached item size
    addendum = "\n# Item size limit\n-I 2M"
    files.append("/etc/memcached.conf", addendum, use_sudo=True)
    sudo("service memcached restart")

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
    # Are we running setup() right now? If so, skip this check.
    if env.get("setup_running", False):
        return

    # Are we running ensure_environment() already? If so, skip this check to
    # prevent infinite loops.
    if env.get("ensure_environment_running", False):
        return
    env.ensure_environment_running = True

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

    # Are we running emptydb() or loaddb() right now? If so, skip the database
    # check.
    if env.get("db_running", False):
        return

    # Has some database been loaded?
    dbs = int(psql("SELECT COUNT(*) FROM pg_stat_database;").strip())
    if dbs < 4:
        print ""
        print "***** "
        print "***** A database has not been loaded. Please run either:"
        print "***** "
        print "*****   $ fab emptydb"
        print "***** "
        print "***** to install an empty database, or:"
        print "***** "
        print "*****   $ fab loaddb"
        print "***** "
        print "***** to load a database dump."
        print "***** "
        exit(-1)

@task
def psql(cmd=None, *args):
    """
    Run the given Postgres command as user postgres. If no command is
    specified, open an interactive psql shell.

    When called from Python code, performs string interpolation on the command
    with the subsequent arguments, and produces machine-readable output.
    """
    ensure_environment()
    if cmd:
        return sudo("psql -AXqt -c " + pipes.quote(cmd % args), user="postgres")
    else:
        interactive("sudo -u postgres psql; exit")

@task
def emptydb(owner="esp", interactive=True):
    """
    Delete any existing Postgres database and replace it with an empty one.

    This task additionally rotates the database credentials and regenerates
    local_settings.py.
    """
    env.db_running = True
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

    # Run Django migrations, etc. (unless being called from loaddb, below)
    if interactive:
        refresh()
        print "***** "
        print "***** Creating the first admin account on the website."
        print "***** Please configure credentials when prompted."
        print "***** "
        manage("createsuperuser")

@task
def loaddb(filename=None):
    """
    If filename is given, load the (decrypted, uncompressed) database dump at
    that local path into the Postgres database.

    If filename is not given, download the dump over HTTP, prompting the user
    for the URL if one has not been previously provided.

    Automatically detects the dump format and proper username.
    """
    env.db_running = True
    ensure_environment()

    # Clean up existing dumpfile, if present
    run("rm -f " + env.encfab + "dbdump")

    if filename:
        put(filename, env.encfab + "dbdump")
    else:
        # Get or prompt for HTTP download settings. These settings are saved in
        # dbconfig in the encrypted part of the Vagrant VM, which makes it
        # easier for people to work with different chapters' databasees in
        # different VMs.
        if files.exists(env.encfab + "dbconfig"):
            contents = run("cat " + env.encfab + "dbconfig")
            config = json.loads(contents)
        else:
            url = prompt("Download URL:")
            config = {
                "url": url,
            }
            escaped_config = pipes.quote(json.dumps(config))
            run("echo " + escaped_config + " > " + env.encfab + "dbconfig")

        # Download database dump into VM
        escaped_url = pipes.quote(config["url"])
        run("wget " + escaped_url + " -O " + env.encfab + "dbdump")

    # HACK: detect the Postgres user used in the dump. We run strings in case
    # the dump is in binary format, then we look for the grant for an arbitrary
    # table, program_class. The result should be like one of the following:
    #
    #   ALTER TABLE public.program_class OWNER TO umbc;
    #   GRANT ALL ON TABLE program_class TO esp;
    #
    # ...which we can then parse to get the user. :D
    query = "ALTER TABLE public.program_class OWNER TO|GRANT ALL ON TABLE program_class TO"
    contents = run("strings " + env.encfab + "dbdump | grep -E '" + query + "'")
    pg_owner = contents.split()[-1][:-1]

    # Reset the database
    emptydb(pg_owner, interactive=False)

    # Load the database dump using the appropriate command for the format
    if "PostgreSQL custom database dump" in run("file " + env.encfab + "dbdump"):
        sudo("pg_restore --verbose --dbname=" + pipes.quote(env.dbname) +
             " --exit-on-error --jobs=2 " + env.encfab + "dbdump",
             user="postgres")
    else:
        sudo("psql --dbname=" + pipes.quote(env.dbname) +
             " --set='ON_ERROR_STOP=on' -f " + env.encfab + "dbdump",
             user="postgres")

    # Run Django migrations, etc.
    refresh()

    # Cleanup
    run("rm -f " + env.encfab + "dbdump")

@task
def dumpdb(filename="devsite_django.sql"):
    """
    Creates a dump of a database.
    This has not been tested on the production server.
    """
    ensure_environment()

    sys.path.insert(0, 'esp/esp/')
    from local_settings import DATABASES
    default_db = DATABASES['default']

    sudo("PGHOST=%s PGPORT=%s PGDATABASE=%s PGUSER=%s PGPASSWORD=%s pg_dump > %s%s" %
         (pipes.quote(default_db['HOST']), pipes.quote(default_db['PORT']), pipes.quote(env.dbname),
         pipes.quote(default_db['USER']), pipes.quote(default_db['PASSWORD']), pipes.quote(env.rbase), pipes.quote(filename)))

def gen_password(length):
    return "".join([random.choice(string.letters + string.digits) for i in range(length)])

@task
def refresh():
    """
    Re-synchronize the remote environment with the codebase. For use when
    switching branches or jumping around the history in git.

      - upgrades and downgrades Python and Ubuntu packages
      - removes orphaned *.pyc files, runs Django migrations and does whatever
        else the update management command does
    """
    ensure_environment()

    run(env.rbase + "esp/update_deps.sh --virtualenv=" + env.venv)
    manage("update")

def interactive(cmd):
    """
    Open an interactive shell running the given command.

    Fabric doesn't do a good job with interactive shells, so use vagrant ssh
    instead. This is a hack, and makes the assumption that our target is the
    default vagrant VM, which  may not be true in the future.
    """
    local("vagrant ssh -c '" + cmd + "'")

@task
def manage(cmd):
    """
    Run a manage.py command in the remote host.
    """
    ensure_environment()

    basecmd = cmd.split(" ")[0]

    if basecmd in ["shell", "shell_plus"]:
        interactive(env.rbase + "esp/manage.py " + cmd)
    else:
        if basecmd.startswith("runserver") and cmd == basecmd:
            print "*** WARNING: 'fab manage:runserver' won't work right. ***"
            print "***            use 'fab runserver' instead.           ***"
        with cd(env.rbase + "esp"):
            run("python manage.py " + cmd)

@task
def runserver():
    """
    A shortcut for 'manage.py runserver' with the appropriate settings.
    """
    ensure_environment()

    manage("runserver 0.0.0.0:8000")

try:
    from local_fabfile import *
except ImportError:
    pass
