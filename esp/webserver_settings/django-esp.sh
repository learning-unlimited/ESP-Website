#!/bin/bash

PROJDIR="/esp/esp/esp"
HOSTNAME="`hostname`"
PORT="3033"

cd $PROJDIR

exec /usr/bin/env - \
  PYTHONPATH="../python:.." \
  ./manage.py runfcgi method=prefork host=$HOSTNAME port=$PORT $@

