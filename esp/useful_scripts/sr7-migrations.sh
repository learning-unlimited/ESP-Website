#!/bin/sh

./manage.py migrate --fake-initial contenttypes
./manage.py migrate --fake-initial auth
./manage.py migrate --fake-initial reversion
./manage.py migrate --fake
./manage.py migrate --fake program 0002
./manage.py migrate --fake qsd 0002
./manage.py migrate
