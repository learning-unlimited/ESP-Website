#!/bin/bash -e

# This script will install the package dependencies for this website install
# that cannot be installed via apt.

if [ $(echo "$(lsb_release -rs) >= 20" | bc) -eq 1 ]; then
  sudo apt install -y curl
else
  sudo apt-get install -y curl
fi

# Install Node.js + npm via NodeSource if npm isn't already available
# (the distro npm package has broken dependencies on Ubuntu 20+)
if ! command -v npm &> /dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  if [ $(echo "$(lsb_release -rs) >= 20" | bc) -eq 1 ]; then
    sudo apt install -y nodejs
  else
    sudo apt-get install -y nodejs
  fi
fi

if [[ ":$PATH:" == *":/usr/bin:"* ]]
then
    # explicitly pass --prefix /usr to npm
    sudo -H npm install --prefix /usr less@3.13.1 -g
else
    # no /usr/bin? hopefully this doesn't happen, let npm guess
    sudo -H npm install less@3.13.1 -g
fi
