#!/bin/sh

MEMCACHED_SERVER="127.0.0.1"
DATABASE_SERVER="127.0.0.1"
REMOTE_SERVER_HOSTNAME="$1"

DBNAME=""
DBPASSWD=""
DBKEY=""

# Give us a nice fancy sources.list
cp /etc/apt/sources.list /etc/apt/sources.list.pre-esp

cat >/etc/apt/sources.list <<EOF
deb http://ubuntu.media.mit.edu/ubuntu/ gutsy main restricted
deb-src http://ubuntu.media.mit.edu/ubuntu/ gutsy main restricted
deb http://ubuntu.media.mit.edu/ubuntu/ gutsy-updates main restricted
deb-src http://ubuntu.media.mit.edu/ubuntu/ gutsy-updates main restricted
deb http://ubuntu.media.mit.edu/ubuntu/ gutsy universe
deb-src http://ubuntu.media.mit.edu/ubuntu/ gutsy universe
deb http://ubuntu.media.mit.edu/ubuntu/ gutsy-updates universe
deb-src http://ubuntu.media.mit.edu/ubuntu/ gutsy-updates universe
deb http://security.ubuntu.com/ubuntu gutsy-security main restricted
deb-src http://security.ubuntu.com/ubuntu gutsy-security main restricted
deb http://security.ubuntu.com/ubuntu gutsy-security universe
deb-src http://security.ubuntu.com/ubuntu gutsy-security universe
EOF

aptitude update
aptitude dist-upgrade -y

# Install the basic packages that we need for a basic fcgi layer, that we can use
aptitude install -y python-django python-imaging python-flup python-setuptools texlive imagemagick subversion exim4 libmemcache0 python-psycopg dvipng python-dns

# Extra packages that we might need in some setups
#aptitude install -y memcached postgresql-8.1 lighttpd

# install stuff to make remote login happen
aptitude install -y openssh-server openssh-client

# Install our editors-of-choice
#aptitude install -y emacs vim


# Set up ESP-Website code
mkdir /esp
cd /esp
svn co http://esp.mit.edu/code/esp-project/trunk/esp
chgrp -R www-data /esp/esp/public/media
chmod -R g+w /esp/esp/public/media

# Install random extra packages
cd /esp/esp/esp/3rdparty
tar xzvf python-memcached-latest.tar.gz
cd python-memcached-1.40
python setup.py install

cd /esp/esp/esp/3rdparty
tar xzvf iCalendar-0.11.tgz
cd iCalendar
python setup.py install

# Install settings.py file and dependencies
cat >/esp/esp/esp/aws_settings.py <<EOF
DATABASE_HOST = '$DATABASE_SERVER'
CACHE_BACKEND="memcached://$MEMCACHED_SERVER:11211/?timeout=120"
EOF

cat >/esp/esp/esp/database_settings.py <<EOF
DATABASE_USER = '$DBNAME'             # Not used with sqlite3.
DATABASE_PASSWORD = '$DBPASSWD'         # Not used with sqlite3.
SECRET_KEY = '$DBKEY'
EOF

# Install and run initscript for Python
ln -s /esp/esp/webserver_settings/django-esp /etc/init.d/
update-rc.d django-esp defaults
/etc/init.d/django-esp start
