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
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CLOSURE_COMPILER_PATH = '/usr/lib/closure/bin'

SECRET_KEY = '%(secret_key)s'

ALLOWED_HOSTS = ['localhost']

GOOGLE_MAPS_EMBED_KEY = ''

######################
# Transport security #
######################
# The following are derived from DEBUG in esp/settings.py and normally need no
# override:
#
#   SESSION_COOKIE_SECURE = not DEBUG
#   CSRF_COOKIE_SECURE    = not DEBUG
#   SECURE_SSL_REDIRECT   = not DEBUG
#   SECURE_HSTS_SECONDS   = 0 if DEBUG else 3600
#
# Assigning any of them here overrides the derived value.  Uncomment what your
# deployment needs.

# Set this ONLY if the site is served exclusively through a TLS-terminating
# reverse proxy (Nginx, an ALB, Varnish with TLS in front, ...) that always
# sets X-Forwarded-Proto AND strips any client-supplied copy of the header.
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# https://docs.djangoproject.com/en/5.2/ref/middleware/#http-strict-transport-security
# Once HTTPS has been stable for a while, ramp HSTS up: 3600 -> 86400 ->
# 31536000.
# SECURE_HSTS_SECONDS = 31536000

# Only enable this once EVERY subdomain of the site's domain serves valid
# HTTPS.
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Do not enable this without a deliberate decision to keep the domain
# and all its subdomains on HTTPS indefinitely.
# SECURE_HSTS_PRELOAD = True

# Set this if the site is NOT served over HTTPS at all
# SECURE_SSL_REDIRECT = False
