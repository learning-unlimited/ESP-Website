#!/bin/bash -e

# This script will install the package dependencies for this website install
# that cannot be installed via apt-get.

sudo apt-get install -y curl
#curl -sL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
#sudo apt-get install -y nodejs
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.37.2/install.sh | bash
sudo nvm install 0.10

if [[ ":$PATH:" == *":/usr/bin:"* ]]
then
    # explicitly pass --prefix /usr to npm
    sudo -H npm install --prefix /usr less@1.3.1 -g
else
    # no /usr/bin? hopefully this doesn't happen, let npm guess
    sudo -H npm install -g less@1.3.1
fi
