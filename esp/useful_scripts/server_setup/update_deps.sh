#!/bin/bash -e

# This script will install or update the dependencies for this website install.
# It reads the list of required Ubuntu packages from /esp/packages_base.txt
# (and optionally /esp/packages_prod.txt) and the list of required PyPI
# packages from /esp/requirements.txt and installs any that are missing. You
# should run this whenever either of those files changes.
#
# The script will automatically detect whether a virtualenv is present
# (see comments in make_virtualenv.sh) and activate it accordingly.

# Parse options
OPTSETTINGS=`getopt -o 'p' -l 'prod' -- "$@"`

eval set -- "$OPTSETTINGS"

while [ ! -z "$1" ]
do
  case "$1" in
    -p) MODE_PROD=true;;
    --prod) MODE_PROD=true;;
     *) break;;
  esac

  shift
done

while [[ ! -f "$PWD/esp/packages_base.txt" || ! -f "$PWD/esp/packages_prod.txt" || ! -f "$PWD/esp/requirements.txt" ]]; do
    if [[ "$PWD" == "/" ]]; then
	echo "Not in project tree: couldn't find requirements files"
	exit 1
    fi
    cd ..
done

sudo apt-get install -y $(< "$PWD/esp/packages_base.txt")
if [[ "$MODE_PROD" ]]
then
    sudo apt-get install -y $(< "$PWD/esp/packages_prod.txt")
fi

[[ -f "$PWD/env/bin/activate" ]] && source "$PWD/env/bin/activate"
pip install -r "$PWD/esp/requirements.txt"
