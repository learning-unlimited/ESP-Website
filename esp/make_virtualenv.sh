#!/bin/bash -e

# This script will "migrate" an existing server setup so that it uses
# virtualenv (see http://www.virtualenv.org/).
#
# Virtualenv tips:
#
# This script will create a virtualenv in the directory /env, where /
# is the root of this repository. If a virtualenv is present at that
# location, manage.py and esp.wsgi (i.e. Apache) will automatically
# detect and activate it so that the libraries installed within will
# be visible to the website code.
#
# You can test whether your manage.py is using virtualenv by using
# "manage.py shell", importing something, and seeing where it's from,
# e.g.
#
# > import reversion
# > reversion.__file__
# '/path/to/env/lib/python3.7/site-packages/reversion/__init__.py'
#
# If the result starts with the path to the repo, rather than
# something like /usr/lib, then virtualenv auto-activation is not
# working.
#
# If for some reason you're running code not through manage.py (for
# instance, a standalone script), you'll need to activate virtualenv
# before running the script in order for the libraries within to be
# visible to your code. You can do this using `source
# /path/to/env/bin/activate`.
#
# Alternatively, if you're writing a standalone Python script that
# will be run frequently, you can copy the lines from manage.py that
# handle auto-activation into your script.
#
# Dependencies are managed using a requirements file. If you need to
# add a pip dependency, add it to /esp/requirements.txt where / is the
# root of this repository.
#
# If for some reason you need to install a package without or before
# adding it to requirements.txt, use:
#
# $ source /path/to/ESP-Website/env/bin/activate
# $ python -m pip install $package
#
# You can generate a new requirements file from your currently
# installed packages using `python -m pip freeze`, which is an alternative way
# of updating requirements.txt (but be careful about adding spurious
# dependencies this way).
#
# To install newly-added dependencies, run the script
# /esp/update_deps.sh: this will read requirements.txt and install any needed
# packages to your virtualenv if present (or to your global site-packages
# otherwise). You should do this whenever requirements.txt changes.

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SCRIPT_SOURCE" ]
do
  SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_SOURCE")" && pwd)"
  SCRIPT_SOURCE="$(readlink "$SCRIPT_SOURCE")"
  [[ "$SCRIPT_SOURCE" != /* ]] && SCRIPT_SOURCE="$SCRIPT_DIR/$SCRIPT_SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_SOURCE")" && pwd)"
BASEDIR="$(cd -P "$SCRIPT_DIR/.." && pwd)"

# The directory to store the virtualenv can be supplied as an argument.
if [[ "$#" -lt "1" ]]
then
    VENVDIR="$BASEDIR/env"
else
    VENVDIR=$1
fi

PYTHON="${PYTHON:-python3.7}"

echo "Creating Virtualenv in $VENVDIR (using $PYTHON)"

# Ensure virtualenv is available for the chosen interpreter without using sudo.
if ! "$PYTHON" -c "import virtualenv" >/dev/null 2>&1; then
    echo "virtualenv not found for $PYTHON."

    if [[ "$EUID" -eq 0 ]]; then
        echo "Installing virtualenv into system site-packages (running as root)."
        "$PYTHON" -m pip install "virtualenv>=1.10"
    else
        echo "Installing virtualenv into user site-packages (no sudo)."
        "$PYTHON" -m pip install --user "virtualenv>=1.10"
        echo "Note: user installs typically go under ~/.local/. If needed, ensure ~/.local/bin is on PATH."
    fi
fi

"$PYTHON" -m virtualenv "$VENVDIR" --always-copy
