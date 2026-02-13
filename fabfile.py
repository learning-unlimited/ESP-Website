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
#   - Take care when using c.local() to run commands locally. Make sure to
#     construct local paths using os.path.join() (here imported as join()), and
#     do not assume the presence of Unix utilities like find and sed.
#
#     In addition, use CONFIG["lbase"] to construct absolute paths when referring
#     to local files, since fab may be invoked from anywhere in the source tree.
#

from fabric import task, Connection, Config
from invoke import run as local_run

import json
import os
import platform
import random
import shlex
import string
import subprocess
import sys

from os.path import join


# ---------------------------------------------------------------------------
# Configuration (replaces the old fabric 1.x env object)
# ---------------------------------------------------------------------------
CONFIG = {
    # Remote base directory, with trailing /
    "rbase": "/home/vagrant/devsite/",
    # Remote virtualenv directory, with trailing /
    "venv": "/home/vagrant/venv/",
    # Local base directory, e.g. C:\Users\Tim\ESP-Website
    "lbase": os.path.dirname(os.path.abspath(__file__)),
    # Name of the Postgres database
    "dbname": "devsite_django",
    # Location where Fabric can store db-related files, with trailing /
    "encfab": "/mnt/encrypted/fabric/",
}

# Runtime flags (replaces env.setup_running, etc.)
_flags = {
    "setup_running": False,
    "ensure_environment_running": False,
    "db_running": False,
    "ensure_environment_done": False,
}


# ---------------------------------------------------------------------------
# Helper: get a Connection to the Vagrant VM
# ---------------------------------------------------------------------------
def get_connection():
    """
    Return a fabric.Connection to the default Vagrant VM.

    This replaces the old fabtools.vagrant.vagrant() call and the implicit
    env.hosts configuration.  It shells out to ``vagrant ssh-config`` and
    parses the result so that Fabric can connect over SSH.
    """
    result = subprocess.run(
        ["vagrant", "ssh-config"],
        capture_output=True, text=True, cwd=CONFIG["lbase"],
    )
    if result.returncode != 0:
        print("")
        print("***** ")
        print("***** Fabric encountered a fatal exception when loading the Vagrant configuration!")
        print("***** Make sure that Vagrant is running:")
        print("*****")
        print("*****   $ vagrant status")
        print("*****   $ vagrant up")
        print("***** ")
        sys.exit(1)

    ssh_info = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if " " in line:
            key, value = line.split(None, 1)
            ssh_info[key.lower()] = value

    connect_kwargs = {}
    if "identityfile" in ssh_info:
        connect_kwargs["key_filename"] = ssh_info["identityfile"]

    # Default to pty=True for all run/sudo calls, matching Fabric 1 behavior.
    # This is needed for interactive prompts (cryptsetup, sudo, etc.) on the
    # Vagrant VM.
    cfg = Config(overrides={"run": {"pty": True}})

    return Connection(
        host=ssh_info.get("hostname", "127.0.0.1"),
        user=ssh_info.get("user", "vagrant"),
        port=int(ssh_info.get("port", 2222)),
        connect_kwargs=connect_kwargs,
        config=cfg,
    )


# ---------------------------------------------------------------------------
# Helpers that replace fabric.contrib.files utilities
# ---------------------------------------------------------------------------
def remote_exists(c, path):
    """Return True if *path* exists on the remote host (replaces files.exists)."""
    return c.run("test -e " + shlex.quote(path), warn=True).ok


def remote_append(c, filename, text, use_sudo=False):
    """
    Append *text* to *filename* on the remote host if it is not already
    present (replaces files.append).
    """
    quoted_text = shlex.quote(text)
    cmd = "grep -qF {text} {file} || echo {text} >> {file}".format(
        text=quoted_text, file=shlex.quote(filename),
    )
    if use_sudo:
        c.sudo(cmd)
    else:
        c.run(cmd)


def upload_template(c, local_path, remote_path, context):
    """
    Read a local template, perform Python string-formatting with *context*,
    and write the result to *remote_path* (replaces files.upload_template).
    """
    with open(local_path) as f:
        rendered = f.read() % context

    # Write via a temp file to avoid shell-escaping issues with large content
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(rendered)
        tmp_path = tmp.name
    try:
        c.put(tmp_path, remote_path)
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def gen_password(length):
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def interactive_cmd(cmd):
    """
    Open an interactive shell running the given command.

    Fabric doesn't do a good job with interactive shells, so use vagrant ssh
    instead.  This is a hack, and makes the assumption that our target is the
    default vagrant VM, which may not be true in the future.
    """
    subprocess.run(["vagrant", "ssh", "-c", cmd], cwd=CONFIG["lbase"])


def _get_encvg(c):
    """Determine the encrypted volume group name based on Ubuntu version."""
    ubuntu_version = c.run(
        "lsb_release -r | awk '{print $2}'", warn=True,
    ).stdout.strip()
    mapping = {
        "24.04": "ubuntu--vg-keep_1",
        "22.04": "ubuntu--vg-keep_1",
        "20.04": "vgvagrant-keep_1",
        "12.04": "ubuntu--12--vg-keep_1",
    }
    if ubuntu_version not in mapping:
        raise ValueError(
            "Unrecognized version of Ubuntu: " + ubuntu_version +
            ". Web Team needs to update fabfile.py to add the "
            "partition name for this VM."
        )
    return mapping[ubuntu_version]


# ---------------------------------------------------------------------------
# psql helper (also a task — see below)
# ---------------------------------------------------------------------------
def _psql(c, cmd=None, *args, **kwargs):
    """
    Run the given Postgres command as user postgres.  If no command is
    specified, open an interactive psql shell.

    When called from Python code, performs string interpolation on the command
    with the subsequent arguments, and produces machine-readable output.
    """
    _ensure_environment(c)
    if cmd:
        formatted = cmd % args
        return c.sudo(
            "psql -AXqt -c " + shlex.quote(formatted),
            user="postgres",
            **kwargs,
        )
    else:
        interactive_cmd("sudo -i -u postgres psql; exit")


# ---------------------------------------------------------------------------
# ensure_environment (replaces @runs_once)
# ---------------------------------------------------------------------------
def _ensure_environment(c):
    """
    Ensure that the environment is fully configured.  If so, print no output
    and return.  If not, attempt to fix the problem (e.g. some things need to
    be done every time the VM boots) or else print instructions and terminate.

    For efficiency, the result of this function is cached for the duration of
    a run of fab.  We assume that an already-configured environment will not
    become un-configured.
    """
    # Are we running setup() right now? If so, skip this check.
    if _flags["setup_running"]:
        return

    # Prevent re-entrant calls (replaces @runs_once)
    if _flags["ensure_environment_running"]:
        return
    if _flags["ensure_environment_done"]:
        return
    _flags["ensure_environment_running"] = True

    # Has setup() been run?
    if not remote_exists(c, "/fab-setup-done"):
        print("")
        print("***** ")
        print("***** The Vagrant VM has not been configured. Please run:")
        print("***** ")
        print("*****   $ fab setup")
        print("***** ")
        sys.exit(-1)

    encvg = _get_encvg(c)

    # Ensure that the encrypted partition has been mounted (must be done after
    # every boot, and can't be done automatically by Vagrant :/)
    if c.sudo("df | grep encrypted | wc -l", warn=True).stdout.strip() != "1":
        check = c.sudo("ls -l /dev/mapper/encrypted &> /dev/null ; echo $?")
        if check.stdout.strip() != "0":
            print("***** ")
            print("***** Opening the encrypted partition for data storage.")
            print("***** Please enter your passphrase when prompted.")
            print("***** ")
            # Use vagrant ssh for interactive passphrase prompt
            interactive_cmd("sudo cryptsetup luksOpen /dev/mapper/%s encrypted" % encvg)
            c.sudo("mount /dev/mapper/encrypted /mnt/encrypted")
        else:
            print("***** ")
            print("***** Something went wrong when mounting the encrypted partition.")
            print("***** Aborting.")
            sys.exit(-1)

    # Are we running emptydb() or loaddb() right now? If so, skip the database
    # check.
    if _flags["db_running"]:
        _flags["ensure_environment_running"] = False
        _flags["ensure_environment_done"] = True
        return

    c.run("chmod 755 /home/vagrant", warn=True)

    # Make sure the postgresql service is running
    c.sudo("service postgresql start")

    # Has some database been loaded?
    result = _psql(c, "SELECT COUNT(*) FROM pg_stat_database;", warn=True)
    dbs = int(result.stdout.strip())
    if dbs < 4:
        print("")
        print("***** ")
        print("***** A database has not been loaded. Please run either:")
        print("***** ")
        print("*****   $ fab emptydb")
        print("***** ")
        print("***** to install an empty database, or:")
        print("***** ")
        print("*****   $ fab loaddb")
        print("***** ")
        print("***** to load a database dump.")
        print("***** ")
        sys.exit(-1)

    # Did `setup()` fail to create the symlinked folders?
    fp = CONFIG["rbase"] + "esp/public/media/"
    if not remote_exists(c, fp + "images") or not remote_exists(c, fp + "styles"):
        print("One of the symlinks `esp/public/media/images` or ")
        print("`.../styles` failed to be created. Try re-running with ")
        print("escalated privileges or contact the web team for more help.")
        sys.exit(-1)

    _flags["ensure_environment_running"] = False
    _flags["ensure_environment_done"] = True


# ---------------------------------------------------------------------------
# Internal helpers for manage, refresh, and emptydb
# ---------------------------------------------------------------------------
def _manage(c, cmd):
    """Run a manage.py command on the remote host."""
    _ensure_environment(c)

    basecmd = cmd.split(" ")[0]

    if basecmd in ["shell", "shell_plus", "createsuperuser", "changepassword"]:
        interactive_cmd("cd " + CONFIG["rbase"] + "esp && source " + CONFIG["venv"] + "bin/activate && python3 manage.py " + cmd)
    else:
        if basecmd.startswith("runserver") and cmd == basecmd:
            print("*** WARNING: 'fab manage:runserver' won't work right. ***")
            print("***            use 'fab runserver' instead.           ***")
        with c.cd(CONFIG["rbase"] + "esp"):
            c.run("source " + CONFIG["venv"] + "bin/activate && python3 manage.py " + cmd)


def _refresh(c):
    """Re-synchronize the remote environment with the codebase."""
    _ensure_environment(c)
    c.run(CONFIG["rbase"] + "esp/update_deps.sh --virtualenv=" + CONFIG["venv"])
    _manage(c, "update")


def _emptydb(c, owner="esp", interactive_mode=True):
    """
    Internal version of emptydb that works with an existing connection.
    """
    _flags["db_running"] = True
    _ensure_environment(c)

    password = gen_password(12)
    context = {
        "db_user": owner,
        "db_name": CONFIG["dbname"],
        "db_password": password,
        "secret_key": gen_password(64),
    }
    upload_template(
        c,
        join(CONFIG["lbase"], "deploy", "config_templates", "local_settings.py"),
        CONFIG["rbase"] + "esp/esp/local_settings.py",
        context,
    )

    _psql(c, "DROP DATABASE IF EXISTS %s", CONFIG["dbname"])
    _psql(c, "DROP ROLE IF EXISTS %s", owner)
    _psql(c, "CREATE ROLE %s CREATEDB LOGIN PASSWORD '" + password + "'", owner)
    _psql(c, "CREATE DATABASE %s OWNER %s TABLESPACE encrypted", CONFIG["dbname"], owner)

    if interactive_mode:
        _refresh(c)
        print("***** ")
        print("***** Creating the first admin account on the website.")
        print("***** Please configure credentials when prompted.")
        print("***** ")
        _manage(c, "createsuperuser")

    _flags["db_running"] = False


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@task
def setup(c):
    """
    Perform initial configuration of a brand-new VM. May fail if run again.
    """
    c = get_connection()
    _flags["setup_running"] = True

    # Install Ubuntu packages, create a virtualenv and install Python packages.
    c.run(CONFIG["rbase"] + "esp/update_deps.sh --virtualenv=" + CONFIG["venv"])

    # Create and mount the encrypted partition (requires user input)
    c.sudo("apt-get install -y cryptsetup")

    print("***** ")
    print("***** Creating the encrypted partition for data storage.")
    print("***** Please choose a passphrase and type it at the prompts.")
    print("***** ")

    encvg = _get_encvg(c)

    # cryptsetup reads passphrases directly from /dev/tty, which Fabric's
    # Paramiko-based SSH transport can't forward properly. Shell out to
    # `vagrant ssh` for these interactive commands, just as we do for psql.
    interactive_cmd("sudo cryptsetup luksFormat -q /dev/mapper/%s" % encvg)
    interactive_cmd("sudo cryptsetup luksOpen /dev/mapper/%s encrypted" % encvg)
    c.sudo("mkfs.ext4 /dev/mapper/encrypted")
    c.sudo("mkdir -p /mnt/encrypted")
    c.sudo("mount /dev/mapper/encrypted /mnt/encrypted")

    # Create the encrypted tablegroup in Postgres
    c.sudo("chown -R postgres /mnt/encrypted")
    _psql(c, "CREATE TABLESPACE encrypted LOCATION '/mnt/encrypted'")

    # Create a directory on the encrypted partition for miscellaneous storage
    c.sudo("chmod +rx /mnt/encrypted")
    c.sudo("mkdir " + CONFIG["encfab"])
    c.sudo("chmod a+rwx " + CONFIG["encfab"])

    # Automatically activate virtualenv
    remote_append(c, "~/.bash_login", "source %sbin/activate" % CONFIG["venv"])

    # Configure memcached item size
    addendum = "\n# Item size limit\n-I 2M"
    remote_append(c, "/etc/memcached.conf", addendum, use_sudo=True)
    c.sudo("service memcached restart")

    # Symlink media
    if platform.system() == "Windows":
        subprocess.run(
            [join(CONFIG["lbase"], "deploy", "windows_symlink_media.bat")],
            cwd=CONFIG["lbase"],
        )
    else:
        with c.cd(CONFIG["rbase"] + "esp/public/media"):
            c.run("ln -s -T default_images images", warn=True)
            c.run("ln -s -T default_styles styles", warn=True)

    c.sudo("touch /fab-setup-done")
    _flags["setup_running"] = False


@task
def psql(c, cmd=None):
    """
    Run the given Postgres command as user postgres. If no command is
    specified, open an interactive psql shell.
    """
    c = get_connection()
    _psql(c, cmd)


@task
def emptydb(c, owner="esp", interactive_mode="true"):
    """
    Delete any existing Postgres database and replace it with an empty one.

    This task additionally rotates the database credentials and regenerates
    local_settings.py.
    """
    c = get_connection()
    # Fabric 3 passes CLI args as strings; convert to bool
    do_interactive = str(interactive_mode).lower() not in ("false", "0", "no")
    _emptydb(c, owner=owner, interactive_mode=do_interactive)


@task
def loaddb(c, filename=None):
    """
    If filename is given, load the (decrypted, uncompressed) database dump at
    that local path into the Postgres database.

    If filename is not given, download the dump over HTTP, prompting the user
    for the URL if one has not been previously provided.

    Automatically detects the dump format and proper username.
    """
    c = get_connection()
    _flags["db_running"] = True
    _ensure_environment(c)

    # Clean up existing dumpfile, if present
    c.run("rm -f " + CONFIG["encfab"] + "dbdump")

    if filename:
        c.put(filename, CONFIG["encfab"] + "dbdump")
    else:
        # Get or prompt for HTTP download settings
        if remote_exists(c, CONFIG["encfab"] + "dbconfig"):
            contents = c.run("cat " + CONFIG["encfab"] + "dbconfig").stdout
            config = json.loads(contents)
        else:
            url = input("Download URL: ")
            config = {"url": url}
            escaped_config = shlex.quote(json.dumps(config))
            c.run("echo " + escaped_config + " > " + CONFIG["encfab"] + "dbconfig")

        # Download database dump into VM
        escaped_url = shlex.quote(config["url"])
        c.run("wget " + escaped_url + " -O " + CONFIG["encfab"] + "dbdump")

    # HACK: detect the Postgres user used in the dump.
    query = "ALTER TABLE public.program_class OWNER TO|GRANT ALL ON TABLE program_class TO"
    contents = c.run(
        "strings " + CONFIG["encfab"] + "dbdump | grep -E '" + query + "'"
    ).stdout
    pg_owner = contents.split()[-1][:-1]

    # Reset the database
    _emptydb(c, pg_owner, interactive_mode=False)

    # Load the database dump using the appropriate command for the format
    file_type = c.run("file " + CONFIG["encfab"] + "dbdump").stdout
    if "PostgreSQL custom database dump" in file_type:
        c.sudo(
            "pg_restore --verbose --dbname=" + shlex.quote(CONFIG["dbname"]) +
            " --exit-on-error --jobs=2 " + CONFIG["encfab"] + "dbdump",
            user="postgres",
        )
    else:
        c.sudo(
            "psql --dbname=" + shlex.quote(CONFIG["dbname"]) +
            " --set='ON_ERROR_STOP=on' -f " + CONFIG["encfab"] + "dbdump",
            user="postgres",
        )

    # Run Django migrations, etc.
    _refresh(c)

    # Cleanup
    c.run("rm -f " + CONFIG["encfab"] + "dbdump")
    _flags["db_running"] = False


@task
def dumpdb(c, filename="devsite_django.sql"):
    """
    Creates a dump of a database.
    This has not been tested on the production server.
    """
    c = get_connection()
    _ensure_environment(c)

    sys.path.insert(0, "esp/esp/")
    from settings import DATABASES
    default_db = DATABASES["default"]

    c.sudo(
        "PGHOST=%s PGPORT=%s PGDATABASE=%s PGUSER=%s PGPASSWORD=%s pg_dump > %s%s" % (
            shlex.quote(default_db["HOST"]),
            shlex.quote(default_db["PORT"]),
            shlex.quote(CONFIG["dbname"]),
            shlex.quote(default_db["USER"]),
            shlex.quote(default_db["PASSWORD"]),
            shlex.quote(CONFIG["rbase"]),
            shlex.quote(filename),
        )
    )


@task
def refresh(c):
    """
    Re-synchronize the remote environment with the codebase. For use when
    switching branches or jumping around the history in git.

      - upgrades and downgrades Python and Ubuntu packages
      - removes orphaned *.pyc files, runs Django migrations and does whatever
        else the update management command does
    """
    c = get_connection()
    _refresh(c)


@task
def manage(c, cmd):
    """
    Run a manage.py command in the remote host.
    """
    c = get_connection()
    _manage(c, cmd)


@task
def runserver(c):
    """
    A shortcut for 'manage.py runserver' with the appropriate settings.
    """
    c = get_connection()
    _ensure_environment(c)
    _manage(c, "runserver 0.0.0.0:8000")


try:
    from local_fabfile import *
except ImportError:
    pass