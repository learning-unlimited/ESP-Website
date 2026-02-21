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

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON not found."
    echo "Install Python 3.7, or run with a different interpreter, e.g.:"
    echo "  PYTHON=python3 bash esp/make_virtualenv.sh"
    echo "  PYTHON=python3.11 bash esp/make_virtualenv.sh"
    exit 1
fi

echo "Creating Virtualenv in $VENVDIR (using $PYTHON)"

# Ensure virtualenv is available for the chosen interpreter without using sudo.
if ! "$PYTHON" -c "import virtualenv" >/dev/null 2>&1; then
    echo "virtualenv not found for $PYTHON."

    if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
        echo "ERROR: pip is not available for $PYTHON."
        echo "Install pip for this interpreter, then rerun."
        exit 1
    fi

    if [[ "$EUID" -eq 0 ]]; then
        echo "Installing virtualenv into system site-packages (running as root)."
        "$PYTHON" -m pip install "virtualenv>=1.10"
    else
        echo "Installing virtualenv into user site-packages (no sudo)."
        if ! "$PYTHON" -m pip install --user "virtualenv>=1.10"; then
            echo ""
            echo "ERROR: Failed to install virtualenv for $PYTHON."
            echo "This can happen on systems where Python is 'externally managed' (PEP 668), e.g. Homebrew Python on macOS."
            echo ""
            echo "Try one of the following:"
            echo "  1) Install virtualenv via pipx (recommended):"
            echo "       pipx install virtualenv"
            echo "  2) Install a different Python (e.g. python.org installer or pyenv) and rerun with:"
            echo "       PYTHON=python3.x bash esp/make_virtualenv.sh"
            echo "  3) If you know what you're doing, you may allow pip to modify an externally-managed env (not recommended):"
            echo "       $PYTHON -m pip install --user --break-system-packages virtualenv"
            echo ""
            exit 1
        fi
        echo "Note: user installs typically go under ~/.local/. If needed, ensure ~/.local/bin is on PATH."
    fi
fi

"$PYTHON" -m virtualenv "$VENVDIR" --always-copy
