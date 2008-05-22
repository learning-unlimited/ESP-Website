#!/bin/bash

/usr/bin/psql uchicagosplash -c 'DELETE FROM django_session WHERE expire_date < now(); VACUUM;'
