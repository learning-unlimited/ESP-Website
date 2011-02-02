#!/bin/bash

# ESP dev server creation script for Ubuntu 10.04
# Michael Price, December 2010

# Parameters
GIT_REPO="http://diogenes.learningu.org/git/esp-project.git"
#GIT_REPO="espuser@esp.mit.edu:/esp/git/esp-project.git"
DROPBOX_STARTUP_SCRIPT="/etc/rc.local"

# Stuff for random password generation
MATRIX="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
LENGTH="8"

# TODO
# Dependency installation
# Database dump loading

#CURDIR=`dirname $0`
CURDIR=`pwd`

# Parse options
OPTSETTINGS=`getopt -o 'ah' -l 'all,reset,deps,git,settings,db,dropbox,apache,help' -- "$@"`
E_OPTERR=65
if [ "$#" -eq 0 ]
then   # Script needs at least one command-line argument.
  echo "Usage: $0 -(option) [-(option) ...] [sitedir]"
  echo "Type '$0 -h' for help."
  exit $E_OPTERR
fi  

eval set -- "$OPTSETTINGS"

while [ ! -z "$1" ]
do
  case "$1" in
    -a) MODE_ALL=true;;
    -h) MODE_USAGE=true;;
    --all) MODE_ALL=true;;
    --help) MODE_USAGE=true;;
    --reset) MODE_RESET=true;;
    --deps) MODE_DEPS=true;;
    --dropbox) MODE_DROPBOX=true;;
    --git) MODE_GIT=true;;
    --db) MODE_DB=true;;
    --settings) MODE_SETTINGS=true;;
    --apache) MODE_APACHE=true;;
     *) break;;
  esac

  shift
done

# Display help if desired
if [[ "$MODE_USAGE" ]]
then
    echo "
dev_server_setup.sh - Create or modify Splash development server
Usage:
    ./dev_server_setup.sh [options] [target directory]
Example:
    ./dev_server_setup.sh --all /home/myuser/esp/sitename
Options:
    -a, --all:  Do everything
    -h, --help: Print this help
    --reset:    Reset settings that have been entered (can be used with others)
    --deps:     Install software dependencies
    --git:      Check out a copy of the code
    --dropbox:  Create a Dropbox share for the site's media files
    --db:       Set up a PostgreSQL database
    --settings: Write settings files
    --apache:   Set up Apache to serve the site using mod_wsgi
    
For more detailed documentation, see: 
    http://wiki.learningu.org/Dev_server_setup_script
"
    exit 0
fi

echo "This script creates or modifies an ESP Web site development server."
echo "Different parts of it are controlled with command line options"
echo "(run with --help to see them).  Please follow the directions."
echo "For more detailed documentation, see: "
echo "    http://wiki.learningu.org/Dev_server_setup_script"
echo "You may hit Ctrl-C to exit at any time."
echo

if [ "$2" ]
then
    BASEDIR="$2"
    echo "You have entered the installation directory: $BASEDIR"
    echo "Please confirm that this is the site you want to create/modify"
    echo -n "by typing 'yes' --> "
    read THROWAWAY
    if [[ "$THROWAWAY" != "yes" ]]
    then
        echo "Confirmation not provided.  Exiting."
        exit 0
    else
        echo "Selected site directory $BASEDIR."
    fi
else
    while [[ ! -n $BASEDIR ]]; do
        echo -n "Enter the directory path to this site install --> "
        read BASEDIR
    done
fi

# Load/reset settings
if [[ -e $BASEDIR/.espsettings ]]
then
    if [ "$MODE_RESET" ]
    then
        rm $BASEDIR/.espsettings
        echo "Any settings in $BASEDIR/.espsettings have been reset."
    else
        source $BASEDIR/.espsettings
    fi
fi

# Ensure that directory exists so that we can save settings
mkdir -p $BASEDIR
echo "#!/bin/bash" > $BASEDIR/.espsettings

# Collect settings
# To manually reset: Remove '.espsettings' file in site directory
while [[ ! -n $SITENAME ]]; do 
    echo 
    echo "Enter a label for this site"
    echo -n "  (default = $(basename $BASEDIR)) --> "
    read SITENAME
    SITENAME=${SITENAME:-$(basename $BASEDIR)}
done
echo "SITENAME=\"$SITENAME\"" >> $BASEDIR/.espsettings
echo "Using site label: $SITENAME"

while [[ ! -n $DEPDIR ]]; do 
    echo 
    echo "Enter the directory to use for dependencies"
    echo -n "  (default = `dirname $BASEDIR`/dependencies) --> "
    read DEPDIR
    DEPDIR=${DEPDIR:-`dirname $BASEDIR`/dependencies}
done
echo "Using dependencies temp directory: $DEPDIR"
echo "DEPDIR=\"$DEPDIR\"" >> $BASEDIR/.espsettings
DROPBOX_PATH=${DEPDIR}/dropbox

while [[ ! -n $ESPHOSTNAME ]]; do 
    echo
    echo -n "Enter your site's hostname (without the http://) --> "
    read ESPHOSTNAME
done
echo "The Web site address will be http://$ESPHOSTNAME."
echo "ESPHOSTNAME=\"$ESPHOSTNAME\"" >> $BASEDIR/.espsettings

while [[ ! -n $GROUPEMAIL ]]; do
    echo
    echo -n "Enter your group's contact e-mail address --> "
    read GROUPEMAIL
done
echo "Contact forms on the site will direct mail to $GROUPEMAIL."
echo "GROUPEMAIL=\"$GROUPEMAIL\"" >> $BASEDIR/.espsettings

while [[ ! -n $GROUPNAME ]]; do
    echo
    echo -n "Enter your group's short name (e.g. 'ESP', 'Splash') --> "
    read GROUPNAME
done
echo "GROUPNAME=\"$GROUPNAME\"" >> $BASEDIR/.espsettings

while [[ ! -n $INSTITUTION ]]; do
    echo
    echo -n "Enter your institution (e.g. 'UCLA') --> "
    read INSTITUTION
done
echo "In printed materials and e-mails your group will be referred to as"
echo "$INSTITUTION $GROUPNAME.  To substitute a more defailted name in"
echo "some printed materials, set the 'full_group_name' Tag."
echo "INSTITUTION=\"$INSTITUTION\"" >> $BASEDIR/.espsettings

while [[ ! -n $EMAILHOST ]]; do
    echo 
    echo "Enter the hostname you will be using for e-mail"
    echo -n "  (default = $ESPHOSTNAME) --> "
    read EMAILHOST
    EMAILHOST=${EMAILHOST:-$ESPHOSTNAME}
done
echo "Selected e-mail host: $EMAILHOST"
echo "EMAILHOST=\"$EMAILHOST\"" >> $BASEDIR/.espsettings

while [[ ! -n $ADMINEMAIL ]]; do
    echo 
    echo -n "Please enter your e-mail address --> "
    read ADMINEMAIL
done
echo "Selected admin e-mail: $ADMINEMAIL"
echo "ADMINEMAIL=\"$ADMINEMAIL\"" >> $BASEDIR/.espsettings

while [[ ! -n $DROPBOX_BASE_DIR ]]; do
    echo 
    echo "Please enter a directory path reserved for Dropbox storage"
    echo "  (default = `dirname $BASEDIR`/dropboxes). This site's Dropbox "
    echo "  share will be mounted as '$SITENAME' within that directory ."
    echo -n "  --> "
    read DROPBOX_BASE_DIR
    DROPBOX_BASE_DIR=${DROPBOX_BASE_DIR:-`dirname $BASEDIR`/dropboxes}
done
echo "Selected Dropbox storage path: $DROPBOX_BASE_DIR"
echo "DROPBOX_BASE_DIR=\"$DROPBOX_BASE_DIR\"" >> $BASEDIR/.espsettings

while [[ ! -n $LOGDIR ]]; do
    echo 
    echo "Please enter a directory path reserved for logs."
    echo "  (default = `dirname $BASEDIR`/logs). Log files from this site "
    echo "  will be given names starting with $SITENAME within that directory. "
    echo -n "  --> "
    read LOGDIR
    LOGDIR=${LOGDIR:-`dirname $BASEDIR`/logs}
done
echo "Selected log directory: $LOGDIR"
echo "LOGDIR=\"$LOGDIR\"" >> $BASEDIR/.espsettings
mkdir -p $LOGDIR

TIMEZONE_DEFAULT="America/New_York"
while [[ ! -n $TIMEZONE ]]; do
    echo 
    echo "Please enter your group's time zone"
    echo -n "  (default $TIMEZONE_DEFAULT) --> "
    read TIMEZONE
    TIMEZONE=${TIMEZONE:-$TIMEZONE_DEFAULT}
done
echo "Selected time zone: $TIMEZONE"
echo "TIMEZONE=\"$TIMEZONE\"" >> $BASEDIR/.espsettings

while [[ ! -n $DBNAME ]]; do
    echo
    echo "Please enter the name of the PostgreSQL database for this site"
    echo -n "  (default = ${SITENAME}_django) --> "
    read DBNAME
    DEFAULT_DBNAME=${SITENAME}_django
    DBNAME=${DBNAME:-$DEFAULT_DBNAME}
done
echo "Selected database name: $DBNAME"
echo "DBNAME=\"$DBNAME\"" >> $BASEDIR/.espsettings

while [[ ! -n $DBUSER ]] ; do
    echo "Please enter the name of the PostgreSQL user for this site"
    echo -n "  (default = $SITENAME) --> "
    read DBUSER
    DBUSER=${DBUSER:-$SITENAME}
done
echo "Selected database username: $DBUSER"
echo "DBUSER=\"$DBUSER\"" >> $BASEDIR/.espsettings

if [[ ! -n $DBPASS ]]
then
    #   Generate random password for database.
    while [ "${n:=1}" -le "$LENGTH" ]
    do
        DBPASS="$DBPASS${MATRIX:$(($RANDOM%${#MATRIX})):1}"
        let n+=1
    done
    echo "Generated random password for database"
else
    echo "Preserved saved database password"
fi
echo "DBPASS=\"$DBPASS\"" >> $BASEDIR/.espsettings

echo "Settings have been entered.  Please check them by looking over the output"
echo -n "above, then press enter to continue or Ctrl-C to quit."
read THROWAWAY

# Update package repositories
apt-get update

# Git repository setup
# To manually reset: Back up .espsettings file in [sitename].old directory, then remove site directory
if [[ "$MODE_GIT" || "$MODE_ALL" ]]
then
    apt-get install -y git-core

    if [[ -e $BASEDIR/esp ]]
    then
        echo "Updating code in $BASEDIR.  Please tend to any conflicts."
        cd $BASEDIR
        git stash
        git pull origin main
        git stash apply
    else
        cd $CURDIR
        if [[ -e $BASEDIR ]]
        then
            echo "Executing: rm -r $BASEDIR.old; mv $BASEDIR $BASEDIR.old"
            rm -r $BASEDIR.old
            mv $BASEDIR $BASEDIR.old
        fi
        echo "Creating site $SITENAME ($BASEDIR)"
        git clone $GIT_REPO $BASEDIR
        if [[ -e $BASEDIR.old/.espsettings ]]
        then
            echo "Executing: cp $BASEDIR.tmp/.espsettings $BASEDIR/"
            cp $BASEDIR.old/.espsettings $BASEDIR/
        fi
    fi
    echo "Git repository has been checked out.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi


# Dependency installation
if [[ "$MODE_DEPS" || "$MODE_ALL" ]]
then

	mkdir -p $DEPDIR
	cd $DEPDIR
	
	#	Get what we can using Ubuntu's package manager
	apt-get install -y build-essential texlive imagemagick subversion dvipng python python-support python-imaging python-flup python-dns python-setuptools python-dns postgresql-8.4 python-psycopg2 libevent-dev python-dev zlib1g-dev libapache2-mod-wsgi inkscape

	#	Fetch and extract files
	if [[ ! -d memcached-1.4.5 ]]
	then
		wget http://memcached.googlecode.com/files/memcached-1.4.5.tar.gz
		tar -xzf memcached-1.4.5.tar.gz
	fi
	if [[ ! -d libmemcached-0.44 ]]
	then
		wget http://launchpad.net/libmemcached/1.0/0.44/+download/libmemcached-0.44.tar.gz
		tar -xzf libmemcached-0.44.tar.gz
	fi
	while [[ ! -d dropbox ]]
	do
        rm -f dropbox.tar.gz
		if [[ `uname -a | grep "_64" | wc -l` != "0" ]]
		then
			wget -O dropbox.tar.gz http://www.dropbox.com/download/?plat=lnx.x86_64
		else
			wget -O dropbox.tar.gz http://www.dropbox.com/download/?plat=lnx.x86
		fi
		tar -xzf dropbox.tar.gz
		mv .dropbox-dist dropbox
	done

	#	Install memcached with additional configuration for init script
	cd $DEPDIR/memcached-1.4.5
	./configure
	make
	make install
	mkdir -p /usr/share/memcached/scripts
	wget -O /usr/share/memcached/scripts/start-memcached http://www.kilentra.net/sandbox/memcached-stuff/start-memcached
	chmod +x /usr/share/memcached/scripts/start-memcached
	wget -O /etc/init.d/memcached http://www.kilentra.net/sandbox/memcached-stuff/memcached
	chmod +x /etc/init.d/memcached
	mkdir -p /etc/default
	echo "ENABLE_MEMCACHED=yes" > /etc/default/memcached
	ln -sf /usr/share/memcached/scripts/start-memcached /etc/rc2.d/S51memcached
	ln -sf /usr/share/memcached/scripts/start-memcached /etc/rc3.d/S51memcached
	ln -sf /usr/share/memcached/scripts/start-memcached /etc/rc4.d/S51memcached
	ln -sf /usr/share/memcached/scripts/start-memcached /etc/rc5.d/S51memcached

	#	Install libmemcached
	cd $DEPDIR/libmemcached-0.44
	./configure --prefix=/usr
	make
	make install

	#	Install python libraries
	python -m easy_install iCalendar
	python -m easy_install django
	python -m easy_install south
	python -m easy_install repoze.profile
	python -m easy_install xlwt
	python -m easy_install simplejson
	python -m easy_install twill

	#	Install sslauth
	if [[ ! -e $BASEDIR/esp/esp/3rdparty/sslauth ]]
	then
		echo "You do not have sslauth (expected path: $BASEDIR/esp/esp/3rdparty/sslauth)."
		echo "This is required only if you want to use Apache to serve your site;"
		echo "Django's manage.py will work fine without it.  If you want to fix this,"
		echo "go back and grab the Git repository by running this script with the "
		echo "--git option."
	else
		cp -r $BASEDIR/esp/esp/3rdparty/sslauth /usr/local/lib/python2.6/dist-packages/
	fi

	cd $DEPDIR
	wget -O django-extensions.tar.gz http://pypi.python.org/packages/source/d/django-extensions/django-extensions-0.6.tar.gz
	tar -zxf django-extensions.tar.gz
	cd django-extensions-0.6
	python setup.py install

	cd $DEPDIR
	wget -O pylibmc.tar.gz http://pypi.python.org/packages/source/p/pylibmc/pylibmc-1.1.1.tar.gz#md5=e43c54e285f8d937a3f1a916256ecc85
	tar -xzf pylibmc.tar.gz
	cd pylibmc-1.1.1
	python setup.py install --with-libmemcached=../libmemcached-0.44/libmemcached

    cd $CURDIR
    
    echo "Dependencies have been installed.  Please check this by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY

fi


# Generation of settings
# To reset: remove database_settings.py and local_settings.py
if [[ "$MODE_SETTINGS" || "$MODE_ALL" ]]
then
    mkdir -p ${BASEDIR}/esp/esp
    
    cat >${BASEDIR}/esp/esp/database_settings.py <<EOF
DATABASE_USER = '$DBUSER'
DATABASE_PASSWORD = '$DBPASS'
EOF

    cat >${BASEDIR}/esp/esp/local_settings.py <<EOF
#                    Edit this file to override settings in                    #
#                              django_settings.py                              #

SITE_INFO = (1, '$ESPHOSTNAME', '$INSTITUTION $GROUPNAME Site')
ADMINS = (
    ('LU Web group','serverlog@lists.learningu.org'),
)
CACHE_PREFIX = "${SITENAME}ESP"

# Default addresses to send archive/bounce info to
DEFAULT_EMAIL_ADDRESSES = {
        'archive': 'learninguarchive@gmail.com',
        'bounces': 'learningubounces@gmail.com',
        'support': '$SITENAME-websupport@lists.learningu.org',
        'membership': '$GROUPEMAIL',
        'default': '$GROUPEMAIL',
        }
ORGANIZATION_SHORT_NAME = '$GROUPNAME'
INSTITUTION_NAME = '$INSTITUTION'
EMAIL_HOST = '$EMAILHOST'

# E-mail addresses for contact form
email_choices = (
    ('general','General ESP'),
    ('esp-web','Web Site Problems'),
    ('splash','Splash!'),
    )
email_addresses = {
    'general': '$GROUPEMAIL',
    'esp-web': '$GROUPEMAIL',
    'splash': '$GROUPEMAIL',
    }
USE_MAILMAN = False
TIME_ZONE = '$TIMEZONE'

# File Locations
PROJECT_ROOT = '$BASEDIR/esp/'
LOG_FILE = '$LOGDIR/$SITENAME-django.log'

# Debug settings
DEBUG = True
DISPLAYSQL = False
TEMPLATE_DEBUG = DEBUG
SHOW_TEMPLATE_ERRORS = DEBUG

# Database
DEFAULT_CACHE_TIMEOUT = 120
DATABASE_ENGINE = 'django.db.backends.postgresql_psycopg2'
#   You can also use this database engine to improve performance at some expense
#   in error reporting capability.
#   DATABASE_ENGINE = 'esp.db.prepared'
SOUTH_DATABASE_ADAPTERS = {'default': 'south.db.postgresql_psycopg2'}
DATABASE_NAME = '$DBNAME'
DATABASE_HOST = 'localhost'
DATABASE_PORT = '5432'

from database_settings import *

MIDDLEWARE_LOCAL = []

# E-mails for contact form
email_choices = (
    ('general', 'General Inquiries'),
    ('web',     'Web Site Problems'),
    )
# Corresponding email addresses                                                                                                                                 
email_addresses = {
    'general': '$GROUPEMAIL',
    'web':     '$SITENAME-websupport@lists.learningu.org',
    }

EOF

    /etc/init.d/memcached restart

    echo "Generated Django settings overrides, saved to:"
    echo "  $BASEDIR/esp/esp/local_settings.py"
    echo "Database login information saved to:"
    echo "  ${BASEDIR}/esp/esp/database_settings.py"

    echo "Settings have been generated.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY

fi

# Dropbox setup
# To reset: 
# - remove line from /etc/rc.local
# - stop Dropbox process from selected home directory
# - remove links to images, styles, uploaded in esp/public/media
# - remove link esp/public/custom_media
# - remove Dropbox folder
if [[ "$MODE_DROPBOX" || "$MODE_ALL" ]]
then

	if [[ ! -e ${DROPBOX_PATH}/dropbox ]]
	then
		echo "Dropbox executable could not be found."
		echo "Expected path was: ${DROPBOX_PATH}/dropbox"
		echo "Please install dependencies using the --deps option."
		exit 1
	fi

    echo "A Dropbox will now be created for this site's media."
    echo "You may be prompted to link this machine to a Dropbox account."
    echo "If so, you'll see a URL that should be copied into a Web browser"
    echo "to establish the link.  You may want to create a new account"
    echo "specific to $INSTITUTION before doing it."
    echo
    echo -n "Once this is complete, type 'ok' and hit enter"
    mkdir -p ${DROPBOX_BASE_DIR}/${SITENAME}
    HOME=${DROPBOX_BASE_DIR}/$SITENAME ${DROPBOX_PATH}/dropbox -i start &

    while [[ $THROWAWAY != "ok" ]]
    do
        echo -n " --> "
        read THROWAWAY
    done
    kill $!

    cat >>$DROPBOX_STARTUP_SCRIPT <<EOF
HOME=${DROPBOX_BASE_DIR}/$SITENAME ${DROPBOX_PATH}/dropboxd &
EOF

    echo "Dropbox for $SITENAME will run on startup from now on."
    echo "To change, edit ${DROPBOX_STARTUP_SCRIPT}."

    HOME=${DROPBOX_BASE_DIR}/$SITENAME nohup ${DROPBOX_PATH}/dropboxd &
    echo "Dropbox has also been started for the current session."

    MEDIADIR=$BASEDIR/esp/public/media
    mkdir -p ${DROPBOX_BASE_DIR}/$SITENAME/Dropbox/media/images
    mkdir -p ${DROPBOX_BASE_DIR}/$SITENAME/Dropbox/media/styles
    mkdir -p ${DROPBOX_BASE_DIR}/$SITENAME/Dropbox/media/uploaded
    DJANGO_DIR=`python -c "import django; print django.__path__[0]"`
    cp -r ${DJANGO_DIR}/contrib/admin/media $MEDIADIR/admin
    ln -sf ${DROPBOX_BASE_DIR}/$SITENAME/Dropbox/media $BASEDIR/esp/public/custom_media
    ln -sf $BASEDIR/esp/public/custom_media/images $BASEDIR/esp/public/media/images
    ln -sf $BASEDIR/esp/public/custom_media/styles $BASEDIR/esp/public/media/styles
    echo "Dropbox-hosted directories have been linked into the site's media."

    mkdir -p $MEDIADIR/uploaded
    chmod -R 777 $MEDIADIR
    
    echo "Dropbox has been set up.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY

fi

# Database setup
# To reset: remove user and DB in SQL
if [[ "$MODE_DB" || "$MODE_ALL" ]]
then
    sudo -u postgres psql template1 -c "CREATE LANGUAGE plpgsql;"
	sudo -u postgres psql -c "CREATE USER $DBUSER CREATEDB;"
	sudo -u postgres psql -c "ALTER ROLE $DBUSER WITH PASSWORD '$DBPASS';"
	sudo -u postgres psql -c "DROP DATABASE $DBNAME;"
	sudo -u postgres psql -c "CREATE DATABASE $DBNAME OWNER ${DBUSER};"
	
	echo "Created a PostgreSQL login role and empty database."
	echo

	echo "You may load an existing database dump file (.sql.gz) if you have one."
	echo "Otherwise we will populate the empty database."
	echo -n "Would you like to load a database dump file? (y/N) --> "
	read USE_DB_DUMP
	USE_DB_DUMP=${USE_DB_DUMP:-N}

	if [[ "$USE_DB_DUMP" == "y" ]]
	then
		#	Instantiate database dump
		cd $CURDIR
		while [[ ! -e $DUMPFILE ]]
		do
			echo "Enter the path (absolute or relative from $CURDIR)"
			echo "to your database dump file.  It should be in gzipped ASCII SQL format."
			echo -n " --> "
			read DUMPFILE
		done
		gunzip $DUMPFILE
		RAWDUMP=${DUMPFILE%.*}

		#	Rename the role temporarily so that permissions are right
		DBOWNER=`grep "ALTER TABLE public.program_class OWNER TO" $RAWDUMP | head -n 1 | cut -d' ' -f 6 | sed "s/;//"`

		sudo -u postgres psql -c "ALTER ROLE $DBUSER RENAME TO $DBOWNER;"
		sudo -u postgres psql $DBNAME -f $RAWDUMP
		sudo -u postgres psql -c "ALTER ROLE $DBOWNER RENAME TO $DBUSER;"
		sudo -u postgres psql -c "ALTER ROLE $DBUSER WITH PASSWORD '$DBPASS';"

		cd $BASEDIR/esp/esp
		./manage.py migrate
		cd $CURDIR

	else
		#	Set up blank database
		echo "Django's manage.py scripts will now be used to initialize the"
		echo "$DBNAME database.  Please follow their directions."

		cd $BASEDIR/esp/esp
		./manage.py syncdb
		./manage.py migrate
		
		cd $CURDIR

	fi
    
    echo "Database has been set up.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi

# Apache setup
# To reset: remove appropriate section from Apache config

if [[ "$MODE_APACHE" || "$MODE_ALL" ]]
then
	APACHE_CONF_DIR=/etc/apache2/conf.d

    cat >$BASEDIR/esp.wsgi <<EOF
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

# Path for ESP code
sys.path.insert(0, '$BASEDIR/esp')

import django.core.handlers.wsgi
django_application = django.core.handlers.wsgi.WSGIHandler()

USE_PROFILER = False

if USE_PROFILER:
    from repoze.profile.profiler import AccumulatingProfileMiddleware
    application = AccumulatingProfileMiddleware(
      django_application,
      log_filename='/tmp/djangoprofile.log',
      discard_first_request=True,
      flush_at_shutdown=True,
      path='/__profile__')
else:
    application = django_application

EOF

	cat >$APACHE_CONF_DIR/enable_vhosts <<EOF
NameVirtualHost *:80
EOF

    cat >$APACHE_CONF_DIR/esp_$SITENAME <<EOF
#   $INSTITUTION $GROUPNAME (automatically generated)
WSGIDaemonProcess $SITENAME processes=1 threads=1 maximum-requests=1000
<VirtualHost *:80>
    ServerName $ESPHOSTNAME

    #   Static files
    Alias /media $BASEDIR/esp/public/media

    #   WSGI scripted Python
    DocumentRoot $BASEDIR/esp/public
    WSGIScriptAlias / $BASEDIR/esp.wsgi
    WSGIProcessGroup $SITENAME
    ErrorLog $LOGDIR/$SITENAME-error.log
    CustomLog $LOGDIR/$SITENAME-access.log combined
    LogLevel warn
</VirtualHost>

EOF
    /etc/init.d/apache2 reload
    echo "Added VirtualHost to Apache configuration $APACHE_CONF_FILE"
    
    echo "Apache has been set up.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi

# Done!
echo "=== Site setup complete: $ESPHOSTNAME ==="
echo "To use, cd to $BASEDIR/esp/esp and try:"
echo "  sudo ./manage.py runserver - runs server on localhost:8000" 
echo "  ./manage.py shell - Python shell where you can import and use models"
echo "You may also use Apache to access the dev site through"
echo "$ESPHOSTNAME; if you don't have DNS set up for this, you"
echo "can add an alias in /etc/hosts."

