#!/bin/bash -e

# This script will install the package dependencies for this website install
# that cannot be installed via apt-get.

sudo apt-get install -y python-software-properties
sudo add-apt-repository -y ppa:chris-lea/node.js
sudo apt-get update
sudo apt-get install -y nodejs
sudo npm install -g less@1.3.1
