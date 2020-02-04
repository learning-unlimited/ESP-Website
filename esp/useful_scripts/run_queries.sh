#!/bin/bash

# Run a query against each chapter site on the LU server.
# usage e.g. $0 "print Program.objects.count()"
#            $0 "$(cat script.py)"

set -e

this_dir="$(readlink -f "${0%/*}")"
base_dir=/lu/sites

cd $base_dir || exit 1
sites=$(ls -d */ | tr -d '/')
echo "$@"
for i in $sites ; do
  if [ -f $i/esp/manage.py ] ; then
    echo -n "$i: "
    python "$this_dir/single_query.py" "$base_dir/$i" "$@"
  fi
done
