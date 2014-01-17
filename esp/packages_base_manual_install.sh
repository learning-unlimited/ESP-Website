#!/bin/bash -e

# This script will install the package dependencies for this website install
# that cannot be installed via apt-get.

if [ -z $(which nodejs) ]
then
    wget http://mirrors.kernel.org/ubuntu/pool/universe/n/nodejs/nodejs_0.6.19~dfsg1-5ubuntu1_amd64.deb -O nodejs.deb
    sudo dpkg -i nodejs.deb
    rm nodejs.deb
fi

if [ -z $(which lessc) ]
then
    wget http://mirrors.kernel.org/ubuntu/pool/universe/l/less.js/node-less_1.3.1~20121105-1_all.deb -O node-less.deb
    sudo dpkg -i node-less.deb
    rm node-less.deb
fi

