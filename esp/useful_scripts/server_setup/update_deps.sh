#!/bin/bash -e

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
