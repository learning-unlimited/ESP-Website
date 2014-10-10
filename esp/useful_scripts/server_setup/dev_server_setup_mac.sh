#!/bin/bash

# ESP dev server creation script for Ubuntu 10.04
# Michael Price, December 2010

# Parameters
#GIT_REPO="http://diogenes.learningu.org/git/esp-project.git"
#GIT_REPO="espuser@esp.mit.edu:/esp/git/esp-project.git"
GIT_REPO="git://github.com/learning-unlimited/ESP-Website.git"

SYS_VERSION="`system_profiler SPSoftwareDataType | grep "System Version:"`"
MACOSX_VERSION="`echo "$SYS_VERSION" | grep "System Version:" | grep -o "10\.[0-9]"`"
case "$MACOSX_VERSION" in
    10.0) MACOSX_CODENAME="Cheetah (dude, you're still running Cheetah??)";;
    10.1) MACOSX_CODENAME="Puma";;
    10.2) MACOSX_CODENAME="Jaguar";;
    10.3) MACOSX_CODENAME="Panther";;
    10.4) MACOSX_CODENAME="Tiger";;
    10.5) MACOSX_CODENAME="Leopard";;
    10.6) MACOSX_CODENAME="Snow Leopard";;
    10.7) MACOSX_CODENAME="Lion";;
    *) MACOSX_CODENAME="(unrecognized version)";;
esac

# Helper method
function die() {
    echo "$1"
    exit -1
}

# Macs tend to distribute packages as .pkg files sitting on mountable filesystems,
# themselves distributed as .dmg files.
# So you have to download the .dmg, mount it, find the .pkg (or .mpkg, a metapackage containing several packages),
# install the .pkg, unmount the image, and remove the .dmg.
function install_dmg_pkg() {
    local DMG="$1"
    if which wget; then  ## Macs don't ship with wget; we install it ourselves after installing MacPorts
        wget -c "$DMG" -O /tmp/disk_image.dmg || die "Error downloading disk image: [$DMG]"
    else
        curl "$DMG" > /tmp/disk_image.dmg || die "Error downloading disk image: [$DMG]"
    fi
    mkdir -p "/tmp/mountpoint"
    hdiutil attach -mountpoint "/tmp/mountpoint" "/tmp/disk_image.dmg"
    if [ -n "`ls /tmp/mountpoint | grep "pkg$"`" ]; then
        installer -verbose -pkg "/tmp/mountpoint/`ls /tmp/mountpoint | grep "pkg$"`" -target / || die "Error installing from disk image [$DMG]"
    else
        echo "Installer is a standalone application; will now launch..."
        open /tmp/mountpoint/*.app
    fi
    hdiutil detach "/tmp/mountpoint" && rm /tmp/disk_image.dmg
    rmdir /tmp/mountpoint
}

function install_zip_pkg() {
    local ZIP="$1"
    if which wget; then
        wget -c "$ZIP" -O /tmp/pkg/zip || die "Error downloading zip file [$ZIP]"
    else
        curl "$ZIP" > /tmp/pkg.zip || die "Error downloading zip file [$ZIP]"
    fi
    pushd .
    cd /tmp/
    mkdir -p pkg
    unzip pkg.zip -d pkg
    if [ -n "`ls /tmp/pkg | grep "pkg$"`" ]; then
        installer -verbose -pkg "/tmp/pkg/`ls /tmp/pkg | grep "pkg$"`" -target / || die "Error installing from zip file [$ZIP]"
    else
        echo "Installer is a standalone application; will now launch..."
        open /tmp/pkg/*.app
    fi
    rm -rf pkg pkg.zip
    popd
}

## Required dependencies
if [ -z "`which port`" ]; then
    echo "WARNING: This installer requires MacPorts!"

    if [ -z "$SYS_VERSION" ]; then
        echo "We can't seem to figure out your MacOS X version; though the following may help:"
        system_profiler SPSoftwareDataType
        echo "You can (probably) download and install MacPorts for this version by"
        echo "following the instructions at <http://www.macports.org/install.php>."

        exit 0
    else
        echo "You appear to be using MacOS X $MACOSX_VERSION \"$MACOSX_CODENAME\"."
    fi

    if [ ! -d "/Developer" ]; then
        echo
        echo "MacPorts requires Apple's Developer Tools, which appear to be missing too."
        echo "You can install them from the CD's that came with your computer, or download"
        echo "the installer from <http://developer.apple.com/xcode/> (free registration required)."
        echo "Please install the Developer tools before proceeding."

        exit 0
    fi

    case "$MACOSX_VERSION" in
        10.0) echo "Error: Unsupported MacOS X version (too old).  You may be able to install MacPorts on your own from macports.org.";exit 0;;
        10.1) echo "Error: Unsupported MacOS X version (too old).  You may be able to install MacPorts on your own from macports.org.";exit 0;;
        10.2) echo "Error: Unsupported MacOS X version (too old).  You may be able to install MacPorts on your own from macports.org.";exit 0;;
        10.3) echo "Error: Unsupported MacOS X version (too old).  You may be able to install MacPorts on your own from macports.org.";exit 0;;
        10.4) install_dmg_pkg "https://distfiles.macports.org/MacPorts/MacPorts-2.0.3-10.4-Tiger.dmg";;
        10.5) install_dmg_pkg "https://distfiles.macports.org/MacPorts/MacPorts-2.0.3-10.5-Leopard.dmg";;
        10.6) install_dmg_pkg "https://distfiles.macports.org/MacPorts/MacPorts-2.0.3-10.6-SnowLeopard.dmg";;
        10.7) install_dmg_pkg "https://distfiles.macports.org/MacPorts/MacPorts-2.0.3-10.7-Lion.dmg";;
        *) echo "Error: Unsupported MacOS X version (too new or otherwise unrecognized).  You may be able to install MacPorts on your own from macports.org.";exit 0;;
    esac

    echo "MacPorts should now be installed.  You may need to log out and log back in again to use it."
    echo "However, this installer is Awesome(tm) and will proceed to use it without logging out and back in."

    ## Set up some MacPorts environment variables
    export PATH="/opt/local/bin:/opt/local/sbin:$PATH"
    export MANPATH=/opt/local/share/man:$MANPATH
fi

# Stuff for random password generation
MATRIX="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
LENGTH="8"

#CURDIR=`dirname $0`
CURDIR=`pwd`

# Parse options
OPTSETTINGS=`getopt ahrdgbsp: $*`
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
    -r) MODE_RESET=true;;
    -d) MODE_DEPS=true;;
    -g) MODE_GIT=true;;
    -b) MODE_DB=true;;
    -s) MODE_SETTINGS=true;;
    -p) MODE_APACHE=true;;
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
    BASEDIR=`echo "$2" | sed -e "s/\/*$//"`

    echo "You have entered the installation directory: $BASEDIR"
    echo "(Note: Trailing slashes have been removed)"
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
    BASEDIR=`echo "$BASEDIR" | sed -e "s/\/*$//"`
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
    echo "Enter the temp directory to use for dependencies"
    echo -n "  (default = `dirname $BASEDIR`/dependencies) --> "
    read DEPDIR
    DEPDIR=${DEPDIR:-`dirname $BASEDIR`/dependencies}
done
echo "Using dependencies temp directory: $DEPDIR"
echo "DEPDIR=\"$DEPDIR\"" >> $BASEDIR/.espsettings

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
echo "In printed materials and e-mails your group will be referred to as"
echo "$INSTITUTION $GROUPNAME.  To substitute a more defailted name in"
echo "some printed materials, set the 'full_group_name' Tag."

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

# Git repository setup
# To manually reset: Back up .espsettings file in [sitename].old directory, then remove site directory
if [[ "$MODE_GIT" || "$MODE_ALL" ]]
then
    export PATH="$PATH:/usr/local/git/bin/"

    if which git; then
        echo "git already installed; not downloading"
    else
        echo "Downloading git"
        case "$MACOSX_VERSION" in
            10.5) which git || if [ -n "`uname -m | grep ppc`" ]; then install_dmg_pkg "http://git-osx-installer.googlecode.com/files/git-1.6.5.1-UNIVERSALbinary-leopard.dmg"; else install_dmg_pkg "http://git-osx-installer.googlecode.com/files/git-1.7.4.4-i386-leopard.dmg"; fi;;
            10.6) which git || install_dmg_pkg "http://git-osx-installer.googlecode.com/files/git-1.7.7-intel-universal-snow-leopard.dmg";;
            10.7) which git || install_dmg_pkg "http://git-osx-installer.googlecode.com/files/git-1.7.7-intel-universal-snow-leopard.dmg";;  ## Lion's Xcode ships with git; may be installed already
            *) echo "Warning:  No binary git package available for this platform.  Installing from source; this may take a while...";port install git-core +universal;;
        esac
    fi

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

    export PATH="$PATH:/usr/local/texlive/2011/bin/universal-darwin/"
    if which latex; then
        echo "LaTeX already installed; not downloading/installing"
    else
        echo "Downloading texlive"
        case "$MACOSX_VERSION" in
            10.3) install_zip_pkg "http://ftp.tug.org/historic/systems/mactex/mactex2010-final-20110528.zip";;
            10.4) install_zip_pkg "http://ftp.tug.org/historic/systems/mactex/mactex2010-final-20110528.zip";;
            10.5) install_zip_pkg "http://mirror.hmc.edu/ctan/systems/mac/mactex/MacTeX.mpkg.zip";;
            10.6) install_zip_pkg "http://mirror.hmc.edu/ctan/systems/mac/mactex/MacTeX.mpkg.zip";;
            10.7) install_zip_pkg "http://mirror.hmc.edu/ctan/systems/mac/mactex/MacTeX.mpkg.zip";;
            *) echo "Warning:  No binary texlive package available for this platform.  Installing from source; this may take a while...";port install texlive +universal;;
        esac
    fi

    if which postgres; then
        echo "PostgreSQL already installed; not downloading/installing.  Please make sure that the 'postgres' user is a PostgreSQL superuser on this system."
    else
        echo "Downloading PostgreSQL"
        case "$MACOSX_VERSION" in
            10.4) install_dmg_pkg "http://get.enterprisedb.com/postgresql/postgresql-9.1.1-1-osx.dmg";;
            10.5) install_dmg_pkg "http://get.enterprisedb.com/postgresql/postgresql-9.1.1-1-osx.dmg";;
            10.6) install_dmg_pkg "http://get.enterprisedb.com/postgresql/postgresql-9.1.1-1-osx.dmg";;
            10.7) install_dmg_pkg "http://get.enterprisedb.com/postgresql/postgresql-9.1.1-1-osx.dmg";;
            *) echo "Warning:  No binary texlive package available for this platform.  Installing from source; this may take a while...";port install postgresql91 +universal;;
        esac
        echo "PostgreSQL requires a reboot after installation, for some boot-time-only kernel parameters to take effect."
        echo "Please reboot, re-run the PostgreSQL installer (which will be on your desktop), and re-run this installer."
        mv /tmp/disk_image.dmg ~/Desktop/PostgreSQL_Installer.dmg
    fi

    #   Get what we can using MacPorts (and what we can't get via any binary package)
    port install ImageMagick +universal
    port install inkscape +universal  ## There is a Snow Leopard inkscape binary, but it doesn't install the CLI tools into $PATH
    port install dvipng +universal
    port install wget +universal  ## There are binaries out there for wget on some platforms; but at this point we might as well just use the package
    port install memcached +universal
    port install libmemcached +universal

    if [[ ! -d selenium-server-standalone-2.8.0 ]]
    then
        mkdir selenium-server-standalone-2.8.0
        cd selenium-server-standalone-2.8.0
        wget http://selenium.googlecode.com/files/selenium-server-standalone-2.8.0.jar
        cd $DEPDIR
    fi

    #    Install python libraries
    virtualenv $BASEDIR/env
    source $BASEDIR/env/bin/activate
    pip install -r $BASEDIR/esp/requirements.txt

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
    ('LU Web group','serverlog@learningu.org'),
)
CACHE_PREFIX = "${SITENAME}ESP"

# Default addresses to send archive/bounce info to
DEFAULT_EMAIL_ADDRESSES = {
        'archive': 'learninguarchive@gmail.com',
        'bounces': 'learningubounces@gmail.com',
        'support': '$SITENAME-websupport@learningu.org',
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
DEBUG_TOOLBAR = True # set to False to globally disable the debug toolbar
USE_PROFILER = False

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
    'web':     '$SITENAME-websupport@learningu.org',
    }

SELENIUM_TEST_RUNNER = 'esp.utils.custom_test_runner.CustomSeleniumTestRunner'
SELENIUM_DRIVERS = 'Firefox'

EOF

    sudo killall memcached ## launchd is shiny and respawns stuff, and I'm lazy

    echo "Generated Django settings overrides, saved to:"
    echo "  $BASEDIR/esp/esp/local_settings.py"
    echo "Database login information saved to:"
    echo "  ${BASEDIR}/esp/esp/database_settings.py"

    echo "Settings have been generated.  Please check them by looking over the"
    echo -n "output above, then press enter to continue or Ctrl-C to quit."
    read THROWAWAY

fi

# Database setup
# To reset: remove user and DB in SQL
if [[ "$MODE_DB" || "$MODE_ALL" ]]
then
    sudo -u postgres psql template1 -c "CREATE LANGUAGE plpgsql;"
    sudo -u postgres psql -c "DROP ROLE IF EXISTS $DBUSER;"
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
        #       Instantiate database dump
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

        #       Rename the role temporarily so that permissions are right
        DBOWNER=`grep "ALTER TABLE public.program_class OWNER TO" $RAWDUMP | head -n 1 | cut -d' ' -f 6 | sed "s/;//"`

        sudo -u postgres psql -c "ALTER ROLE $DBUSER RENAME TO $DBOWNER;"
        sudo -u postgres psql $DBNAME -f $RAWDUMP
        sudo -u postgres psql -c "ALTER ROLE $DBOWNER RENAME TO $DBUSER;"
        sudo -u postgres psql -c "ALTER ROLE $DBUSER WITH PASSWORD '$DBPASS';"

        cd $BASEDIR/esp/esp
        ./manage.py migrate
        cd $CURDIR

    else
        #       Set up blank database
        echo "Django's manage.py scripts will now be used to initialize the"
        echo "$DBNAME database.  Please follow their directions."

        cd $BASEDIR/esp/esp
        ./manage.py syncdb
        ./manage.py migrate

        #   Set initial Site (used in password recovery e-mail)
        sudo -u postgres psql -c "DELETE FROM django_site; INSERT INTO django_site (id, domain, name) VALUES (1, '$ESPHOSTNAME', '$INSTITUTION $GROUPNAME Site');" $DBNAME

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
    APACHE_CONF_DIR=/etc/apache2/extra

    sudo tee $APACHE_CONF_DIR/enable_vhosts <<EOF
NameVirtualHost *:80
EOF

    sudo tee $APACHE_CONF_DIR/esp_$SITENAME <<EOF
#   $INSTITUTION $GROUPNAME (automatically generated)
WSGIDaemonProcess $SITENAME processes=1 threads=1 maximum-requests=1000
<VirtualHost *:80>
    ServerName $ESPHOSTNAME

    #   Static files
    Alias /media $BASEDIR/esp/public/media
    Alias /static $BASEDIR/esp/public/static

    #   WSGI scripted Python
    DocumentRoot $BASEDIR/esp/public
    WSGIScriptAlias / $BASEDIR/esp.wsgi
    WSGIProcessGroup $SITENAME
    ErrorLog $LOGDIR/$SITENAME-error.log
    CustomLog $LOGDIR/$SITENAME-access.log combined
    LogLevel warn
</VirtualHost>

EOF
    sudo apachectl restart
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

