#!/bin/bash

PROJDIR="/esp/stanford/esp"
SOCKET="$PROJDIR/esp.sock"

cd $PROJDIR

exec /usr/bin/env - \
  PYTHONPATH="../python:.." \
  ./manage.py runfcgi socket=$SOCKET $@
