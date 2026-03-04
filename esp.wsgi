#!/usr/bin/env python

from __future__ import absolute_import
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

BASEDIR = os.path.dirname(os.path.realpath(__file__))

ENVDIR = os.path.join(BASEDIR, 'env')

# Path for ESP code
sys.path.insert(0, os.path.join(BASEDIR, 'esp'))

import django.core.wsgi
django_application = django.core.wsgi.get_wsgi_application()

from django.conf import settings

application = django_application

