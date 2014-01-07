#!/usr/bin/env python

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

BASEDIR = os.path.dirname(__file__)

# Path for ESP code
sys.path.insert(0, os.path.join(BASEDIR, 'esp'))

try:
    # activate virtualenv
    activate_this = os.path.join(BASEDIR, 'env/bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))
except IOError:
    pass

import django.core.handlers.wsgi
django_application = django.core.handlers.wsgi.WSGIHandler()

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

