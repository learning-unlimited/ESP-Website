#!/bin/bash -e

while [[ ! -n "$BASEDIR" ]]; do
    echo -n "Enter the root directory path of this site install (it should include a .git file) --> "
    read BASEDIR
done
if [[ ! -f "$BASEDIR/esp/packages.txt" || ! -f "$BASEDIR/esp/requirements.txt" ]]; then
    echo "Couldn't find requirements files for site install at $BASEDIR"
    exit 1
fi
FULLPATH=$(mkdir -p "$BASEDIR"; cd "$BASEDIR"; pwd)
BASEDIR=$(echo "$FULLPATH" | sed -e "s/\/*$//")

sudo apt-get install $(< "$BASEDIR/esp/packages.txt")

sudo pip install virtualenv>=1.10
virtualenv "$BASEDIR/env"
source "$BASEDIR/env/bin/activate"
pip install -r "$BASEDIR/esp/requirements.txt"

cat >/tmp/esp.wsgi <<EOF
try:
    # activate virtualenv
    activate_this = '$BASEDIR/env/bin/activate_this.py'
    execfile(activate_this, dict(__file__=activate_this))
except IOError:
    pass

EOF

cat "$BASEDIR/esp.wsgi" >>/tmp/esp.wsgi
mv /tmp/esp.wsgi "$BASEDIR/esp.wsgi"
