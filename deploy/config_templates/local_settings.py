""" Local system-specific settings. """

from __future__ import absolute_import
import os

SITE_INFO = (1, 'esp-dev.mit.edu', 'MIT ESP Dev Site')
CACHE_PREFIX = "ludev"
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
USE_MAILMAN = False
DEBUG = True
SHOW_TEMPLATE_ERRORS = DEBUG
CACHE_DEBUG = False

DATABASES = {'default':
                {'NAME': '%(db_name)s',
                 'HOST': 'localhost',
                 'PORT': '5432',
                 'ENGINE': 'django.db.backends.postgresql_psycopg2',
                 'USER': '%(db_user)s',
                 'PASSWORD': '%(db_password)s',
                }
            }

MIDDLEWARE_LOCAL = []

EMAIL_HOST_SENDER = 'esp.mit.edu'
ALLOWED_SENDER_EMAIL_DOMAINS = [r'esp\.mit\.edu', r'mit\.edu', r'esp-dev\.mit\.edu']
VARNISH_HOST = None
DEBUG_TOOLBAR = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CLOSURE_COMPILER_PATH = '/usr/lib/closure/bin'

SECRET_KEY = '%(secret_key)s'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
