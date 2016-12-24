#!/bin/bash
#
# Set up the basic environment on a newly-created server.
#

set -euf -o pipefail

if [[ "$#" -ne 1 ]]; then
  >&2 echo "usage: $0 GIT-BRANCH"
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  >&2 echo "This script must be run as root"
  exit 1
fi

if ! id ubuntu >/dev/null 2>&1; then
  >&2 echo "Expected user 'ubuntu' to exist"
  exit 1
fi

# Finish setting up the /lu directory
chown ubuntu:ubuntu /lu
pushd /lu
sudo -u ubuntu git clone https://github.com/learning-unlimited/ESP-Website.git esp-website
pushd /lu/esp-website
git checkout "$1"
popd
popd

# Install initial dependencies
export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y chef
gem install inifile

# Run chef
/lu/esp-website/deploy/chef/tier-web.sh
