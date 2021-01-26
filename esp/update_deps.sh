#!/bin/bash -e

# This script will install or update the dependencies for this website install.
# It reads the list of required Ubuntu packages from packages_base.txt
# (and optionally packages_prod.txt) and the list of required PyPI
# packages from requirements.txt and installs any that are missing. It
# also runs packages_base_manual_install.sh to install any missing
# packages that require manual install. You should run this whenever either of
# those files changes.
#
# The script will automatically detect whether a virtualenv is present
# (see comments in make_virtualenv.sh) and activate it accordingly.

# Parse options
OPTSETTINGS=`getopt -o 'pv:' -l 'prod,virtualenv:' -- "$@"`

eval set -- "$OPTSETTINGS"

while [ ! -z "$1" ]
do
  case "$1" in
    -p | --prod) MODE_PROD=true;;
    -v | --virtualenv) MODE_VIRTUALBOX=true; VIRTUALENV_DIR=$2; shift;;
     *) break;;
  esac

  shift
done

BASEDIR=$(dirname $(dirname $(readlink -e $0)))

sudo apt-get update
xargs sudo apt-get install -y < $BASEDIR/esp/packages_base.txt
$BASEDIR/esp/packages_base_manual_install.sh
if [[ "$MODE_PROD" ]]
then
    xargs sudo apt-get install -y < $BASEDIR/esp/packages_prod.txt
fi

# Install pip
sudo add-apt-repository universe
sudo apt-get install -y curl
curl https://bootstrap.pypa.io/2.7/get-pip.py --output get-pip.py
sudo python2 get-pip.py

# Ensure that the virtualenv exists and is activated.
if [[ -z "$VIRTUAL_ENV" ]]
then
    VIRTUALENV_DIR=${VIRTUALENV_DIR:-$BASEDIR/env}
    if [[ ! -f "$VIRTUALENV_DIR/bin/activate" ]]
    then
        $BASEDIR/esp/make_virtualenv.sh $VIRTUALENV_DIR
    fi
    source "$VIRTUALENV_DIR/bin/activate"
fi

# Install/upgrade pip, setuptools, wheel, and application dependencies.
pip2 install -U pip
pip2 install -U setuptools wheel
pip2 install -U -r "$BASEDIR/esp/requirements.txt"
