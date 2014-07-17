#!/bin/bash -e

# This script will install the package dependencies for this website install
# that cannot be installed via apt-get.

if [ $(uname -m) == 'x86_64' ]; then
  wget http://mirrors.kernel.org/ubuntu/pool/universe/libv/libv8/libv8-3.8.9.20_3.8.9.20-2_amd64.deb -O libv8.deb
  wget http://mirrors.kernel.org/ubuntu/pool/universe/n/nodejs/nodejs_0.6.12~dfsg1-1ubuntu1_amd64.deb -O nodejs.deb
  wget http://mirrors.kernel.org/ubuntu/pool/universe/l/less.js/node-less_1.3.1~20121105-1_all.deb -O node-less.deb
else
  wget http://mirrors.kernel.org/ubuntu/pool/universe/libv/libv8/libv8-3.8.9.20_3.8.9.20-2_i386.deb -O libv8.deb
  wget http://mirrors.kernel.org/ubuntu/pool/universe/n/nodejs/nodejs_0.6.12~dfsg1-1ubuntu1_i386.deb -O nodejs.deb
  wget http://mirrors.kernel.org/ubuntu/pool/universe/l/less.js/node-less_1.3.1~20121105-1_all.deb -O node-less.deb
fi

sudo dpkg -i libv8.deb
sudo dpkg -i nodejs.deb
sudo dpkg -i node-less.deb
rm *.deb

