""" Local system-specific settings. """

import os

SITE_INFO = (1, 'devsite.learningu.org', 'LU Dev Site')
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

EMAIL_HOST_SENDER = 'devsite.learningu.org'
VARNISH_HOST = None
DEBUG_TOOLBAR = True
# Outbound mail is sent through EMAIL_BACKEND
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Inbound mail forwarding (esp/mailgates/mailgate.py) uses MAILGATE_EMAIL_BACKEND.
# It must be an SMTP-style backend, not a Web API backend.
MAILGATE_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# On production, you should use:
# MAILGATE_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#
# A site delivering through a local MTA needs nothing else here. A site relaying
# through SendGrid needs smtp credentials like this:
#
#     SENDGRID_API_KEY = '<your key>'
#     EMAIL_HOST = 'smtp.sendgrid.net'
#     EMAIL_PORT = 587
#     EMAIL_HOST_USER = 'apikey'          # literally the word "apikey"
#     EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
#     EMAIL_USE_TLS = True

CLOSURE_COMPILER_PATH = '/usr/lib/closure/bin'

SECRET_KEY = '%(secret_key)s'

ALLOWED_HOSTS = ['localhost']
