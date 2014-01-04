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
# '/path/to/env/lib/python2.7/site-packages/reversion/__init__.py'
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
# $ pip install $package
#
# You can generate a new requirements file from your currently
# installed packages using `pip freeze`, which is an alternative way
# of updating requirements.txt (but be careful about adding spurious
# dependencies this way).
#
# To install newly-added dependencies, run the script
# /esp/useful_scripts/server_setup/update_deps.sh: this will read
# requirements.txt and install any needed packages to your virtualenv
# if present (or to your global site-packages otherwise). You should
# do this whenever requirements.txt changes.

# Parse options
OPTSETTINGS=`getopt -o 'pc' -l 'prod,usecwd' -- "$@"`

eval set -- "$OPTSETTINGS"

while [ ! -z "$1" ]
do
  case "$1" in
    -p) MODE_PROD=true;;
    -c) BASEDIR=$PWD;;
    --prod) MODE_PROD=true;;
    --usepwd) BASEDIR=$PWD;;
     *) break;;
  esac

  shift
done

while [[ ! -n "$BASEDIR" ]]; do
    echo -n "Enter the root directory path of this site install (it should include a .git file) --> "
    read BASEDIR
done
if [[ ! -f "$BASEDIR/esp/packages_base.txt" || ! -f "$BASEDIR/esp/packages_prod.txt" || ! -f "$BASEDIR/esp/requirements.txt" ]]; then
    echo "Couldn't find requirements files for site install at $BASEDIR"
    exit 1
fi
FULLPATH=$(mkdir -p "$BASEDIR"; cd "$BASEDIR"; pwd)
BASEDIR=$(echo "$FULLPATH" | sed -e "s/\/*$//")

sudo apt-get install -y $(< "$BASEDIR/esp/packages_base.txt")
if [[ "$MODE_PROD" ]]
then
    sudo apt-get install -y $(< "$BASEDIR/esp/packages_prod.txt")
fi

sudo pip install "virtualenv>=1.10"
virtualenv "$BASEDIR/env"
source "$BASEDIR/env/bin/activate"
pip install -r "$BASEDIR/esp/requirements.txt"

cat >/tmp/esp.wsgi <<EOF
try:
    # activate virtualenv
    activate_this = '$BASEDIR/env/bin/activate_this.py'
    execfile(activate_this, dict(__file__=activate_this))
except IOError:
    pass

EOF

cat "$BASEDIR/esp.wsgi" >>/tmp/esp.wsgi
mv /tmp/esp.wsgi "$BASEDIR/esp.wsgi"
