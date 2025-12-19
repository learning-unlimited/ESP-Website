#!/bin/bash -e

# This script will install the package dependencies for a devserver install
# that cannot be installed via apt.

if command -v watchman &> /dev/null && watchman --version | grep -q "20251124.015248.0"; then
    echo "Watchman is already installed."
else
    echo "Installing Watchman"
    wget https://github.com/facebook/watchman/releases/download/v2025.11.24.00/watchman-v2025.11.24.00-linux.zip

    unzip watchman-v2025.11.24.00-linux.zip
    cd watchman-v2025.11.24.00-linux
    sudo mkdir -p /usr/local/{bin,lib} /usr/local/var/run/watchman
    sudo cp bin/* /usr/local/bin
    sudo cp lib/* /usr/local/lib
    sudo chmod 755 /usr/local/bin/watchman
    sudo chmod 2777 /usr/local/var/run/watchman
    
    cd ..
    rm watchman-v2025.11.24.00-linux.zip watchman-v2025.11.24.00-linux
fi
