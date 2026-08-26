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
# Without both of those, a client can assert "https" over plain HTTP and
# request.is_secure() will believe it, bypassing the SSL redirect.  The
# reference Apache + mod_wsgi deployment serves requests directly and must
# NOT set this.
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Once HTTPS has been stable for a while, ramp HSTS up: 3600 -> 86400 ->
# 31536000.  Each step is a promise browsers will not let you take back before
# it expires, so do not skip ahead.
# SECURE_HSTS_SECONDS = 31536000

# Only enable this once EVERY subdomain of the site's domain serves valid
# HTTPS -- it applies to siblings you may not control.
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Submitting to the browser preload list is effectively irreversible for
# months.  Do not enable this without a deliberate decision to keep the domain
# and all its subdomains on HTTPS indefinitely.
# SECURE_HSTS_PRELOAD = True

# Set this if the site is NOT served over HTTPS at all -- with DEBUG = False
# the derived default redirects every request to HTTPS, which is a redirect
# loop on an HTTP-only host.  Also worth setting if TLS terminates somewhere
# that already redirects HTTP to HTTPS (a load balancer, or Apache with a
# Redirect rule): the app-level redirect is then redundant and can interact
# badly with Varnish caching a 301.
# SECURE_SSL_REDIRECT = False
