#!/bin/bash

/usr/bin/psql django -c 'DELETE FROM django_session WHERE expire_date < now(); VACUUM;'
