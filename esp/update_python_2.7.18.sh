sudo apt-get update
sudo apt-get install build-essential checkinstall -y
sudo apt-get install libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev -y
wget https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz
tar xzf Python-2.7.18.tgz
cd Python-2.7.18
sudo ./configure --enable-optimizations
sudo make install
cd ..
rm -rf Python-2.7.18
rm Python-2.7.18.tgz
wget https://bootstrap.pypa.io/pip/2.7/get-pip.py
python get-pip.py "pip==20.3.4"
rm get-pip.py
