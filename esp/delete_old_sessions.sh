#!/bin/bash

sudo -u postgres /usr/bin/psql uchicagosplash -c 'DELETE FROM django_session WHERE expire_date < now()' &>/dev/null
sudo -u postgres /usr/bin/psql django -c 'DELETE FROM django_session WHERE expire_date < now()' &>/dev/null
sudo -u postgres /usr/bin/psql django -c 'VACUUM;' &>/dev/null
sudo -u postgres /usr/bin/psql uchicagosplash -c 'VACUUM;' &>/dev/null
