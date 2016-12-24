#!/bin/bash
#
# Installs dependencies for a web-tier server.
#

set -euf -o pipefail

pushd `dirname "$0"`
./base.rb
./cron.rb
./database.rb
./memcached.rb
./uwsgi.rb
./website.rb
popd
