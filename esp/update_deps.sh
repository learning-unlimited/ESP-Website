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

UBUNTU_VERSION=$(lsb_release -sr)

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

sudo apt update
xargs sudo apt install -y < $BASEDIR/esp/packages_base.txt

# This nodejs/less installation only works on Ubuntu 16+
# The versions on the production server don't seem to break anything, so we'll just skip it
if [ $((${UBUNTU_VERSION%.*}+0)) -ge 16 ]
then
$BASEDIR/esp/packages_base_manual_install.sh
fi

if [[ "$MODE_PROD" ]]
then
    if [ $((${UBUNTU_VERSION%.*}+0)) -ge 20 ]
    then
    xargs sudo apt install -y < $BASEDIR/esp/packages_prod.txt
    else
    xargs sudo apt-get install -y < $BASEDIR/esp/packages_prod_u12.txt
    fi
fi

# Install pip
# How we add the repository depends on the version of Ubuntu
if [ $((${UBUNTU_VERSION%.*}+0)) -gt 12 ]
then
sudo add-apt-repository universe
else
sudo add-apt-repository "deb http://old-releases.ubuntu.com/ubuntu $(lsb_release -sc) universe"
fi

if [ $((${UBUNTU_VERSION%.*}+0)) -ge 20 ]
then
sudo apt update
sudo apt install -y curl
else
sudo apt-get update
sudo apt-get install -y curl
fi

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

sudo curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
python2 get-pip.py

# Install/upgrade pip, setuptools, wheel, and application dependencies.
pip2 install -U pip
pip2 install -U setuptools wheel
pip2 install -U -r "$BASEDIR/esp/requirements.txt"
