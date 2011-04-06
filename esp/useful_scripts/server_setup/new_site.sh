#!/bin/bash

# ESP site creation script
# Michael Price, December 2010

# Parameters
GIT_REPO="http://diogenes.learningu.org/git/esp-project.git"
APACHE_CONF_FILE="/etc/apache2/sites-available/esp_sites.conf"
LOGDIR="/lu/logs"
DJANGO_DIR=`python -c "import django; print django.__path__[0]"`
DROPBOX_BASE_DIR="/lu/dropboxes"
DROPBOX_STARTUP_SCRIPT="/etc/rc.local"
DROPBOX_PATH="/lu/software/dropbox"
MAILMAN_LIST_PASSWORD="oobleck"
MAILMAN_ADMIN="price@kilentra.net"
CRON_FILE="/etc/crontab"

#CURDIR=`dirname $0`
CURDIR=`pwd`

# Parse options
OPTSETTINGS=`getopt -o 'ah' -l 'reset,git,settings,db,dropbox,apache,mailman,cron,help' -- "$@"`
E_OPTERR=65
if [ "$#" -eq 0 ]
then   # Script needs at least one command-line argument.
  echo "Usage: $0 -(option) [-(option) ...] [sitename]"
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
    --dropbox) MODE_DROPBOX=true;;
    --git) MODE_GIT=true;;
    --db) MODE_DB=true;;
    --settings) MODE_SETTINGS=true;;
    --apache) MODE_APACHE=true;;
    --mailman) MODE_MAILMAN=true;;
    --cron) MODE_CRON=true;;
     *) break;;
  esac

  shift
done

# Display help if desired
if [[ "$MODE_USAGE" ]]
then
    echo "
new_site.sh - Create or modify new Splash Web site
Options:
    -a, --all:  Do everything
    -h, --help: Print this help
    --reset:    Reset settings that have been entered (can be used with others)
    --git:      Check out a copy of the code
    --dropbox:  Create a Dropbox share for the site's media files
    --db:       Set up a PostgreSQL database
    --settings: Write settings files
    --apache:   Set up Apache to serve the site using mod_wsgi
    --mailman:  Create a Mailman support list
    --cron:     Add appropriate entry to cron for comm panel e-mail sending
"
    exit 0
fi

echo "This script creates or modifies an ESP Web site."
echo "Different parts of it are controlled with command line options"
echo "(run with --help to see them).  Please follow the directions."
echo "You may hit Ctrl-C to exit at any time."
echo

if [ "$2" ]
then
    SITENAME=`echo "$2" | sed -e "s/\/*$//"`
    echo "You have entered the directory name: $SITENAME"
    echo "(Note: Trailing slashes have been removed)"
    echo "Please confirm that this is the site you want to create/modify"
    echo -n "by typing 'yes' --> "
    read THROWAWAY
    if [[ "$THROWAWAY" != "yes" ]]
    then
        echo "Confirmation not provided.  Exiting."
        exit 0
    else
        echo "Selected site directory $SITENAME."
    fi
else
    while [[ ! -n $SITENAME ]]; do
        echo -n "Enter the directory name of this site --> "
        read SITENAME
    done
    SITENAME=`echo "$SITENAME" | sed -e "s/\/*$//"`
fi

BASEDIR=${CURDIR}/${SITENAME}

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
    echo "Please enter the e-mail address of the initial site administrator"
    echo -n "  --> "
    read ADMINEMAIL
done
echo "Selected admin e-mail: $ADMINEMAIL"
echo "ADMINEMAIL=\"$ADMINEMAIL\"" >> $BASEDIR/.espsettings

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
    DBPASS=`$CURDIR/random_password.sh`
    echo "Generated random password for database"
else
    echo "Preserved saved database password"
fi
echo "DBPASS=\"$DBPASS\"" >> $BASEDIR/.espsettings

echo "Settings have been entered.  Please check them by looking over the output"
echo -n "above, then press enter to continue or Ctrl-C to quit."
read THROWAWAY

# Git repository setup
# To manually reset: Back up .espsettings file in [sitename].old directory, then remove site directory
if [[ "$MODE_GIT" || "$MODE_ALL" ]]
then
    if [[ -e $CURDIR/$SITENAME/esp ]]
    then
        echo "Updating code in $BASEDIR.  Please tend to any conflicts."
        cd $BASEDIR
        git stash
        git pull origin main
        git stash apply
    else
        cd $CURDIR
        if [[ -e $CURDIR/$SITENAME ]]
        then
            echo "Executing: rm -r $CURDIR/$SITENAME.old; mv $CURDIR/$SITENAME $CURDIR/$SITENAME.old"
            rm -r $CURDIR/$SITENAME.old
            mv $CURDIR/$SITENAME $CURDIR/$SITENAME.old
        fi
        echo "Creating site $SITENAME in $CURDIR."
        git clone $GIT_REPO $SITENAME
        if [[ -e $CURDIR/$SITENAME.old/.espsettings ]]
        then
            echo "Executing: cp $CURDIR/$SITENAME.tmp/.espsettings $CURDIR/$SITENAME/"
            cp $CURDIR/$SITENAME.old/.espsettings $CURDIR/$SITENAME/
        fi
    fi
    echo "Git repository has been checked out.  Please check them by looking over the"
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
DEBUG = False
DISPLAYSQL = False
TEMPLATE_DEBUG = DEBUG
SHOW_TEMPLATE_ERRORS = DEBUG

# Database
DEFAULT_CACHE_TIMEOUT = 120
DATABASE_ENGINE = 'postgresql_psycopg2'
#DATABASE_ENGINE = 'esp.db.prepared'
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
    chmod -R 777 ${DROPBOX_BASE_DIR}/$SITENAME/Dropbox/media/uploaded
    cp -r ${DJANGO_DIR}/contrib/admin/media ${DROPBOX_BASE_DIR}/$SITENAME/Dropbox/media/admin
    ln -sf ${DROPBOX_BASE_DIR}/$SITENAME/Dropbox/media $BASEDIR/esp/public/custom_media
    ln -sf $BASEDIR/esp/public/custom_media/images $BASEDIR/esp/public/media/images
    ln -sf $BASEDIR/esp/public/custom_media/styles $BASEDIR/esp/public/media/styles
    ln -sf $BASEDIR/esp/public/custom_media/admin $BASEDIR/esp/public/media/admin
    echo "Dropbox-hosted directories have been linked into the site's media."

    cp -r $MEDIADIR/default_images/* $MEDIADIR/images/
    cp -r $MEDIADIR/default_styles/* $MEDIADIR/styles/
    echo "Default images and styles have been placed in the Dropbox."

    mkdir $MEDIADIR/uploaded
    mkdir $MEDIADIR/uploaded/bio_pictures
    chmod -R 777 $MEDIADIR
    
    echo "Dropbox has been set up.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY

fi

# Database setup
# To reset: remove user and DB in SQL
if [[ "$MODE_DB" || "$MODE_ALL" ]]
then
    sudo -u postgres psql -c "CREATE USER $DBUSER;"
    sudo -u postgres psql -c "ALTER ROLE $DBUSER WITH PASSWORD '$DBPASS';"
    sudo -u postgres psql -c "CREATE DATABASE $DBNAME OWNER ${DBUSER};"
    echo "Created a PostgreSQL login role and empty database."
    
    echo "Django's manage.py scripts will now be used to initialize the"
    echo "$DBNAME database.  Please follow their directions."

    cd $BASEDIR/esp/esp
    ./manage.py syncdb
    ./manage.py migrate
    cd $CURDIR
    
    #   Set initial Site (used in password recovery e-mail)
    sudo -u postgres psql -c "DELETE FROM django_site; INSERT INTO django_site (id, domain, name) VALUES (1, '$ESPHOSTNAME', '$INSTITUTION $GROUPNAME Site');" $DBNAME

    echo "Database has been set up.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi

# Mailman setup
# To reset: remove list manually
if [[ "$MODE_MAILMAN" || "$MODE_ALL" ]]
then
    newlist -q $SITENAME-websupport $ADMINEMAIL $MAILMAN_LIST_PASSWORD
    add_members -r - granite-websupport <<EOF
$ADMINEMAIL
EOF
    echo "Created Mailman list $SITENAME-websupport with initial member $ADMINEMAIL."
    
    echo "Support list has been created.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi

# Apache setup
# To reset: remove appropriate section from Apache config
if [[ "$MODE_APACHE" || "$MODE_ALL" ]]
then
    cat >$BASEDIR/esp.wsgi <<EOF
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

# Path for ESP code
sys.path.insert(0, '/lu/sites/$SITENAME/esp')

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

    cat >>$APACHE_CONF_FILE <<EOF
#   $INSTITUTION $GROUPNAME (automatically generated)
WSGIDaemonProcess $SITENAME processes=1 threads=1 maximum-requests=1000
<VirtualHost *:80 *:81>
    ServerName $ESPHOSTNAME
    ServerAlias $SITENAME-orig.learningu.org

    #   Redirect to be used for failover
    # RedirectMatch (.*) http://$SITENAME-backup.learningu.org\$1

    #   Caching - should use Squid if performance is really important
    # CacheEnable disk /

    #   Static files
    Alias /media $BASEDIR/esp/public/media
    <Location /media>
        DAV on
        <LimitExcept GET HEAD OPTIONS PROPFIND>
            AuthType Basic
            AuthUserFile /lu/auth/dav_auth
            AuthName "$INSTITUTION $GROUPNAME media files"
            Require valid-user
        </LimitExcept>
        ExpiresActive on
        ExpiresDefault "now plus 1 hour"
    </Location>

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

if [[ "$MODE_CRON" || "$MODE_ALL" ]]
then
    cat >>$CRON_FILE <<EOF
* * * * * root $BASEDIR/esp/dbmail_cron.py
EOF
fi

# Done!
echo "=== Site setup complete: $ESPHOSTNAME ==="
IP_ADDRESS=`ifconfig  | grep 'inet addr:'| grep -v '127.0.0.1' | cut -d: -f2 | awk '{ print $1}'`
echo "Please ensure that DNS is configured to provide A and MX records for:"
echo "  $ESPHOSTNAME -> $IP_ADDRESS"
echo "  $SITENAME-orig.learningu.org -> $IP_ADDRESS"
echo "  $SITENAME-backup.learningu.org -> $IP_ADDRESS"
echo "You may also want to add some template overrides that establish"
echo "the initial look and feel of the site."
echo
