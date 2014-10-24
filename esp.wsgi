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

# activate virtualenv
activate_this = os.path.join(ENVDIR, 'bin/activate_this.py')
try:
    execfile(activate_this, dict(__file__=activate_this))
except IOError, e:
    # Check if a virtualenv has been installed and activated from elsewhere.
    # If this has happened, then the VIRTUAL_ENV environment variable should be
    # defined, and we can ignore the IOError.
    # If the variable isn't defined, then we really should be using our own
    # virtualenv, so we re-raise the error.
    if os.environ.get('VIRTUAL_ENV') is None:
        raise e

import django.core.wsgi
django_application = django.core.wsgi.get_wsgi_application()

from django.conf import settings

if settings.USE_PROFILER:
    from repoze.profile.profiler import AccumulatingProfileMiddleware
    application = AccumulatingProfileMiddleware(
      django_application,
      log_filename='/tmp/djangoprofile.log',
      discard_first_request=True,
      flush_at_shutdown=True,
      path='/__profile__')
else:
    application = django_application

