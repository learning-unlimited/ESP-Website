#!/bin/bash -e

# This script will install or update the dependencies for this website
# install. It reads the list of required Ubuntu packages from
# /esp/packages.txt and the list of required PyPI packages from
# /esp/requirements.txt and installs any that are missing. You should
# run this whenever either of those files changes.
#
# The script will automatically detect whether a virtualenv is present
# (see comments in make_virtualenv.sh) and activate it accordingly.

while [[ ! -f "$PWD/esp/packages.txt" || ! -f "$PWD/esp/requirements.txt" ]]; do
    if [[ "$PWD" == "/" ]]; then
	echo "Not in project tree: couldn't find requirements files"
	exit 1
    fi
    cd ..
done

sudo apt-get install $(< "$PWD/esp/packages.txt")

[[ -f "$PWD/env/bin/activate" ]] && source "$PWD/env/bin/activate"
pip install -r "$PWD/esp/requirements.txt"
