#!/bin/bash

# ESP site creation script
# See /docs/dev/deploying.rst for documentation on how to deploy.

# no -u because a bunch of the modes are undefined unless we use them.
set -ef -o pipefail

# Parameters
GIT_REPO="git://github.com/learning-unlimited/ESP-Website.git"
APACHE_CONF_FILE="/etc/apache2/sites-available/esp_sites.conf"
APACHE_REDIRECT_CONF_FILE="/etc/apache2/sites-available/esp_sites/https_redirect.conf"
AUTH_USER_FILE="/lu/auth/dav_auth"
EXIMDIR="/etc/exim4"
APACHE_LOGDIR="/lu/logs"
DJANGO_LOGDIR="/lu/logs/django"
CRON_FILE="/etc/crontab"
WWW_USER="www-data"
DOMAIN="learningu.org"
TIMEZONE_DEFAULT="America/New_York"

# This should probably be /lu/sites
# TODO(benkraft): should we hardcode that we install to /lu/sites?
CURDIR=`pwd`

# TODO(benkraft): it would be nice if more of these steps were idempotent, so
# that if something failed somewhere you could just rerun it instead of
# completing or undoing it manually.

# Parse options
OPTSETTINGS=`getopt -o 'ah' -l 'reset,all,git,settings,db,apache,cron,exim,help' -- "$@"`
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
    --git) MODE_GIT=true;;
    --db) MODE_DB=true;;
    --settings) MODE_SETTINGS=true;;
    --apache) MODE_APACHE=true;;
    --cron) MODE_CRON=true;;
    --exim) MODE_EXIM=true;;
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
    --db:       Set up a PostgreSQL database
    --settings: Write settings files
    --apache:   Set up Apache to serve the site using mod_wsgi
    --cron:     Add appropriate entry to cron for comm panel email sending
    --exim:     Add appropriate exim4 config for email handling
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
    echo "Enter your site's hostname (without the https://)"
    echo -n "  (default = $SITENAME.$DOMAIN) --> "
    read ESPHOSTNAME
    ESPHOSTNAME=${ESPHOSTNAME:-$SITENAME.$DOMAIN}
done
echo "The Web site address will be http://$ESPHOSTNAME."
echo "ESPHOSTNAME=\"$ESPHOSTNAME\"" >> $BASEDIR/.espsettings

while [[ ! -n $GROUPEMAIL ]]; do
    echo
    echo -n "Enter your group's contact email address --> "
    read GROUPEMAIL
done
echo "Contact forms on the site will direct mail to $GROUPEMAIL."
echo "GROUPEMAIL=\"$GROUPEMAIL\"" >> $BASEDIR/.espsettings

while [[ ! -n $INSTITUTION ]]; do
    echo
    echo -n "Enter your institution (e.g. 'UCLA') --> "
    read INSTITUTION
done
echo "INSTITUTION=\"$INSTITUTION\"" >> $BASEDIR/.espsettings

while [[ ! -n $GROUPNAME ]]; do
    echo
    echo -n "Enter your group's short name (e.g. 'ESP', 'Splash') --> "
    read GROUPNAME
done
echo "GROUPNAME=\"$GROUPNAME\"" >> $BASEDIR/.espsettings
echo "In printed materials and emails your group will be referred to as"
echo "$INSTITUTION $GROUPNAME.  To substitute a more detailed name in"
echo "some printed materials, set the 'full_group_name' Tag."

while [[ ! -n $EMAILHOST ]]; do
    echo
    echo "Enter the hostname you will be using for email"
    echo -n "  (default = $ESPHOSTNAME) --> "
    read EMAILHOST
    EMAILHOST=${EMAILHOST:-$ESPHOSTNAME}
done
echo "Selected email host: $EMAILHOST"
echo "EMAILHOST=\"$EMAILHOST\"" >> $BASEDIR/.espsettings

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
    DBPASS=`openssl rand -base64 12`
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
if [[ "$MODE_GIT" || "$MODE_ALL" ]] ; then
    echo -n "Enter the current release branch --> "
    read GIT_BRANCH
    if [[ -e "$BASEDIR/.git" ]] ; then
        echo "Updating code in $BASEDIR.  Please tend to any conflicts."
        cd "$BASEDIR"
        if ! git diff --exit-code >/dev/null ; then
            DIFF=true
            git stash
        fi
        git pull origin ${GIT_BRANCH}
        if [[ "$DIFF" ]] ; then
            # Only apply the stash if we made one.
            git stash apply
        fi
    else
        # We will almost certainly have created $BASEDIR already; get it out of
        # the way for git.
        if [[ -e "$BASEDIR" ]] ; then
            echo "Executing: rm -rf $BASEDIR.old; mv $BASEDIR $BASEDIR.old"
            rm -rf "$BASEDIR.old"
            mv "$BASEDIR" "$BASEDIR.old"
        fi
        echo "Creating site $SITENAME in $CURDIR."
        git clone "$GIT_REPO" "$SITENAME"
        cd "$BASEDIR"
        git checkout "$GIT_BRANCH"
        if [[ -e "$BASEDIR.old/.espsettings" ]] ; then
            echo "Executing: cp $BASEDIR.tmp/.espsettings $BASEDIR/"
            cp "$BASEDIR.old/.espsettings" "$BASEDIR/"
        fi
        if [[ "$(ls -A "$BASEDIR.old")" = ".espsettings" ]] ; then
            # If all that's left in $BASEDIR.old is the .espsettings file,
            # which we've now copied to $BASEDIR, get rid of it.
            rm -rf "$BASEDIR.old"
        fi
    fi

    
    ./esp/make_virtualenv.sh
    ./esp/update_deps.sh --prod
    chown -R $WWW_USER:$WWW_USER "$BASEDIR"

    echo "Git repository has been checked out, and dependencies have been installed"
    echo "with Python libraries in a local virtualenv.  Please check them by looking"
    echo -n "over the output above, then press enter to continue or Ctrl-C to quit."
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
    ('LU Web group','serverlog@$DOMAIN'),
)
CACHE_PREFIX = "${SITENAME}ESP"

# Default addresses to send archive/bounce info to
DEFAULT_EMAIL_ADDRESSES = {
        'archive': 'splashwebsitearchive@learningu.org',
        'bounces': 'emailbounces@learningu.org',
        'support': '$GROUPEMAIL',
        'membership': '$GROUPEMAIL',
        'default': '$GROUPEMAIL',
        }
ORGANIZATION_SHORT_NAME = '$GROUPNAME'
INSTITUTION_NAME = '$INSTITUTION'
EMAIL_HOST = '$EMAILHOST'
EMAIL_HOST_SENDER = EMAIL_HOST

USE_MAILMAN = False
TIME_ZONE = '$TIMEZONE'

# File Locations
PROJECT_ROOT = '$BASEDIR/esp/'
LOG_FILE = '$DJANGO_LOGDIR/$SITENAME-django.log'

# Debug settings
DEBUG = False
SHOW_TEMPLATE_ERRORS = DEBUG
DEBUG_TOOLBAR = True # set to False to globally disable the debug toolbar

# Database
DEFAULT_CACHE_TIMEOUT = 120
DATABASE_ENGINE = 'django.db.backends.postgresql_psycopg2'
DATABASE_NAME = '$DBNAME'
DATABASE_HOST = 'localhost'
DATABASE_PORT = '5432'

VARNISH_HOST = 'localhost'
VARNISH_PORT = '80'

from database_settings import *

MIDDLEWARE_LOCAL = []

SECRET_KEY = '`openssl rand -base64 48`'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
ALLOWED_HOSTS = ['$ESPHOSTNAME']

EOF

    chown -R $WWW_USER:$WWW_USER "$BASEDIR"
    # TODO(benkraft): This shouldn't be necessary; we should just set things up
    # to get the right perms on creation.
    for ext in .shell.log .log ; do
        touch "$DJANGO_LOGDIR/$SITENAME-django$ext"
        chown $WWW_USER:$WWW_USER "$DJANGO_LOGDIR/$SITENAME-django$ext"
    done

    echo "Generated Django settings overrides, saved to:"
    echo "  $BASEDIR/esp/esp/local_settings.py"
    echo "Database login information saved to:"
    echo "  ${BASEDIR}/esp/esp/database_settings.py"

    echo "Settings have been generated.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY

fi

MEDIADIR="$BASEDIR/esp/public/media"
[[ -e "$MEDIADIR/images" ]] || ln -s "$MEDIADIR/default_images" "$MEDIADIR/images"
[[ -e "$MEDIADIR/styles" ]] || ln -s "$MEDIADIR/default_styles" "$MEDIADIR/styles"

mkdir -p $MEDIADIR/uploaded
chmod -R u+rwX,go+rX $MEDIADIR
mkdir -p /tmp/esptmp__${SITENAME}ESP
chmod -R u+rwX,go+rX /tmp/esptmp__${SITENAME}ESP
echo "Default images and styles have been symlinked."

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

    cd $BASEDIR/esp
    ./manage.py migrate
    ./manage.py createsuperuser
    # This will prompt before it (potentially) clobbers files.  Since it's a
    # new site, there's definitely nothing to clobber and we can just say yes
    # automatically.  With `set -o pipefail`, this will exit 141 (SIGPIPE), so
    # we need `|| true` to prevent the script from exiting failure.
    yes yes | ./manage.py collectstatic || true
    chown -R $WWW_USER:$WWW_USER "$BASEDIR"
    cd $CURDIR

    #   Set initial Site (used in password recovery email)
    # TODO(benkraft): do this in python.
    sudo -u postgres psql -c "DELETE FROM django_site; INSERT INTO django_site (id, domain, name) VALUES (1, '$ESPHOSTNAME', '$INSTITUTION $GROUPNAME Site');" $DBNAME

    echo "Database has been set up.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi

# Apache setup
# To reset: remove appropriate section from Apache config
if [[ "$MODE_APACHE" || "$MODE_ALL" ]]
then
    # TODO(benkraft): we should put each site in a separate conf file, and just
    # make sure they all get imported.
    # TODO(benkraft): we should attempt to factor much of the shared config out
    # into a single file used by all sites, so it's easier to update.
    cat >>$APACHE_CONF_FILE <<EOF

#   $INSTITUTION $GROUPNAME (automatically generated)
WSGIDaemonProcess $SITENAME processes=2 threads=1 maximum-requests=500 display-name=${SITENAME}wsgi
<VirtualHost *:80 *:81>
    ServerName $ESPHOSTNAME

    Include $APACHE_REDIRECT_CONF_FILE

    #   Caching - should use Squid if performance is really important
    CacheEnable disk /

    #   Static files
    Alias /media $BASEDIR/esp/public/media
    Alias /static $BASEDIR/esp/public/static
    Alias /favicon.ico $BASEDIR/esp/public/media/images/favicon.ico

    #   WSGI scripted Python
    DocumentRoot $BASEDIR/esp/public
    WSGIScriptAlias / $BASEDIR/esp.wsgi
    WSGIProcessGroup $SITENAME
    WSGIApplicationGroup %{GLOBAL}
    ErrorLog $APACHE_LOGDIR/$SITENAME-error.log
    CustomLog $APACHE_LOGDIR/$SITENAME-access.log combined
    LogLevel warn
</VirtualHost>

EOF
    service apache2 graceful
    # TODO(benkraft): put the renewal script in git too.
    /lu/scripts/certbot/renew_lu.py
    echo "Added VirtualHost to Apache configuration $APACHE_CONF_FILE"

    echo "Apache has been set up, and a new SSL cert has been requested."
    echo "Please check them by looking over the output above, then press"
    echo -n "enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi

if [[ "$MODE_CRON" || "$MODE_ALL" ]]
then
    # Rather than run all dbmail_cron procs every 5 minutes, we choose a random
    # offset for each.
    # TODO(benkraft): we should just figure out the right cron syntax to have
    # cron do this magically, without having to do `sleep` ourselves, and
    # update both this and existing cron jobs.
    sleep_sec="$(( (RANDOM % 5) * 60))"
    if [[ "$sleep_sec" -eq 0 ]] ; then
        sleep_cmd=""
    else
        sleep_cmd="sleep $sleep_sec ; "
    fi
    cat >>"$CRON_FILE" <<EOF
*/5 * * * * root $sleep_cmd$BASEDIR/esp/dbmail_cron.py
EOF

    # TODO(benkraft): actually echo the added line so there's something to
    # check.
    echo "cron has been set up.  Please check the config by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi

if [[ "$MODE_EXIM" || "$MODE_ALL" ]] ; then
    cat >>"$EXIMDIR/virtual/$ESPHOSTNAME" <<EOF
*: "|$BASEDIR/esp/mailgates/mailgate.py"
EOF
    # The line we want to edit looks like
    # dc_other_hostnames='foo.learningu.org;bar.learningu.org;baz.learningu.org'
    # and we want to add another entry to it.
    sed --in-place=.bak "s/^\\(dc_other_hostnames='.*\\)'$/\\1;$ESPHOSTNAME'/" "$EXIMDIR/update-exim4.conf.conf"
    update-exim4.conf
    exim -bt test@$ESPHOSTNAME

    echo "exim4 has been set up.  Please check the config by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY
fi

# Done!
# Let's let the human do the /etc commit since they may want to separate out
# other changes, or make sure everything is right, before doing so.
echo "=== Site setup complete: $ESPHOSTNAME ==="
echo "You may wish to commit your changes to the /etc git repo.  You may"
echo "also wish to set up a theme and create additional administrators."
echo
