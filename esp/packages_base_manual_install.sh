#!/bin/bash -e

# This script will install the package dependencies for this website install
# that cannot be installed via apt.

if [ $(echo "$(lsb_release -rs) >= 20" | bc) -eq 1 ]; then 
  sudo apt install -y curl
 else
  sudo apt-get install -y curl
fi
if [ $(echo "$(lsb_release -rs) >= 20" | bc) -eq 1 ]; then 
  sudo apt install -y nodejs
 else
  sudo apt-get install -y nodejs
fi

if [[ ":$PATH:" == *":/usr/bin:"* ]]
then
    # explicitly pass --prefix /usr to npm
    sudo -H npm install --prefix /usr less@1.7.5 -g
else
    # no /usr/bin? hopefully this doesn't happen, let npm guess
    sudo -H npm install less@1.7.5 -g
fi

curl https://bootstrap.pypa.io/pip/3.7/get-pip.py -o get-pip-3.7.py
python3.7 get-pip-3.7.py
rm get-pip-3.7.py
