#!/bin/bash -e

# This script will install the package dependencies for this website install
# that cannot be installed via apt-get.

sudo apt-get install -y python-software-properties
curl -fsSL https://deb.nodesource.com/setup_12.x | sudo -E bash -
sudo apt-get update
sudo apt-get install -y nodejs

if [[ ":$PATH:" == *":/usr/bin:"* ]]
then
    # explicitly pass --prefix /usr to npm
    sudo -H npm install -g --prefix /usr less@1.3.1
else
    # no /usr/bin? hopefully this doesn't happen, let npm guess
    sudo -H npm install -g less@1.3.1
fi

# increase memcached limit
sudo su -c '(echo ""; echo "-I 3M") >> /etc/memcached.conf'

