#!/usr/bin/env python

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

BASEDIR = os.path.dirname(os.path.realpath(__file__))

#   Hack for Vagrant development environments: separate virtualenv dir.
import getpass
if getpass.getuser() == 'vagrant':
    ENVDIR = '/home/vagrant/devsite_virtualenv'
else:
    ENVDIR = os.path.join(BASEDIR, 'env')

# Path for ESP code
sys.path.insert(0, os.path.join(BASEDIR, 'esp'))

# Check if a virtualenv has been installed and activated from elsewhere.
# If this has happened, then the VIRTUAL_ENV environment variable should be
# defined.
# If the variable isn't defined, then activate our own virtualenv.
if os.environ.get('VIRTUAL_ENV') is None:
    activate_this = os.path.join(ENVDIR, 'bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

import django.core.wsgi
django_application = django.core.wsgi.get_wsgi_application()

from django.conf import settings

application = django_application

