#!/bin/bash

PROJDIR="/esp/esp/esp"
SOCKET="$PROJDIR/esp.sock"

cd $PROJDIR

exec /usr/bin/env - \
  PYTHONPATH="../python:.." \
  ./manage.py runfcgi socket=$SOCKET $@
