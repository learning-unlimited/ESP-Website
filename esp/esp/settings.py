__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

import os
import warnings
import tempfile
import django

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
# Django expects BASE_DIR
BASE_DIR = PROJECT_ROOT
# set by shell_plus and script_setup (via esp.utils.shell_utils); should also
# be set in any other scripts that get called manually, but not in scripts that
# get run unattended by e.g. cron.
IS_IN_SCRIPT = os.environ.get("DJANGO_IS_IN_SCRIPT", "False") == "True"

# Configure Django to support ESP
from django_settings import *

# Import system-specific settings
from local_settings import *

# Do this here so we have access to PROJECT_ROOT
TEMPLATES[0]['DIRS'].append(os.path.join(PROJECT_ROOT, 'templates'))
TEMPLATES[0]['DIRS'].append(django.__path__[0] + '/forms/templates')
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

# Ensure database settings are set properly
if len(DATABASES['default']['USER']) == 0:
    try:
        DATABASES['default']['USER'] = DATABASE_USER
    except:
        raise Exception("You need to supply either DATABASES['default']['USER'] or DATABASE_USER in database_settings.py")
if len(DATABASES['default']['PASSWORD']) == 0:
    try:
        DATABASES['default']['PASSWORD'] = DATABASE_PASSWORD
    except:
        raise Exception("You need to supply either DATABASES['default']['PASSWORD'] or DATABASE_PASSWORD in database_settings.py")
if len(DATABASES['default']['NAME']) == 0:
    try:
        DATABASES['default']['NAME'] = DATABASE_NAME
    except:
        raise Exception("You need to supply either DATABASES['default']['NAME'] or DATABASE_NAME in local_settings.py")

SERVER_EMAIL = 'server@%s' % EMAIL_HOST_SENDER

############################################

# compute some derived settings
MEDIA_ROOT = os.path.join(PROJECT_ROOT, MEDIA_ROOT_DIR)
STATIC_ROOT = os.path.join(PROJECT_ROOT, STATIC_ROOT_DIR)

# We log to LOG_FILE always at level LOG_LEVEL (INFO by default), log to the
# console at level LOG_LEVEL if DEBUG=True, mail admins (i.e. serverlog) at
# level ERROR if DEBUG=False, and log to sentry at level WARNING if set up.
# DisallowedHost errors and deprecation warnings don't go to email ever.
# In scripts, we log to the console in a shorter format, to a separate log
# file, and not to email or sentry.
if SENTRY_DSN:
    sentry_handler = {
        'level': 'WARNING',
        'filters': ['require_not_in_script'],
        'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        'dsn': SENTRY_DSN,
    }
else:
    sentry_handler = {
        'class': 'logging.NullHandler',
    }

warnings.simplefilter("default", PendingDeprecationWarning)

if LOG_FILE.endswith('.log'):
    SHELL_LOG_FILE = LOG_FILE[:-4] + '.shell.log'
else:
    SHELL_LOG_FILE = LOG_FILE + '.shell'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s %(name)s:%(lineno)s] %(levelname)s: %(message)s',
        },
        'brief': {
            'format': '%(levelname)s: %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_in_script': {
            '()': 'esp.utils.log.RequireInScript',
        },
        'require_not_in_script': {
            '()': 'esp.utils.log.RequireNotInScript',
        },
    },
    'handlers': {
        'file': {
            'level': LOG_LEVEL,
            # logrotate will take care of rotation if desired
            'class': 'logging.FileHandler',
            'filters': ['require_not_in_script'],
            # LOG_FILE is set in django_settings or overridden in
            # local_settings
            'filename': LOG_FILE,
            'formatter': 'verbose',
        },
        'filescript': {
            'level': LOG_LEVEL,
            # logrotate will take care of rotation if desired
            'class': 'logging.FileHandler',
            'filters': ['require_in_script'],
            'filename': SHELL_LOG_FILE,  # computed from LOG_FILE above
            'formatter': 'verbose',
        },
        'console': {
            'level': LOG_LEVEL,
            'filters': ['require_debug_true', 'require_not_in_script'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'consolescript': {
            'level': LOG_LEVEL,
            'filters': ['require_in_script'],
            'class': 'logging.StreamHandler',
            'formatter': 'brief',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false', 'require_not_in_script'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
            'formatter': 'verbose',
        },
        'sentry': sentry_handler,
    },
    # We don't have a root logger, because it for various reasons ends up
    # confusing runserver_plus and getting doubled log output.  I can't figure
    # out a good way around that, and we should ideally be logging everything
    # under 'esp' anyway.
    'loggers': {
        'django.security.DisallowedHost': {
            # Don't bother with the DisallowedHost errors.
            'handlers': ['file', 'console'],
            'propagate': False,
        },
        # TODO(benkraft): until 1.9 we need to have the following two handlers
        # around to override django's.  In 1.9 we will be able to remove them,
        # and just override 'django'.
        'django.security': {
            'handlers': ['file', 'filescript', 'console', 'consolescript',
                         'mail_admins', 'sentry'],
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['file', 'filescript', 'console', 'consolescript',
                         'mail_admins', 'sentry'],
            'level': 'DEBUG',
        },
        'django': {
            'handlers': ['file', 'filescript', 'console', 'consolescript',
                         'mail_admins', 'sentry'],
            'level': 'DEBUG',
        },
        'py.warnings': {
            'handlers': ['file', 'filescript', 'console', 'consolescript',
                         'sentry'],
        },
        'esp': {
            'handlers': ['file', 'filescript', 'console', 'consolescript',
                         'mail_admins', 'sentry'],
            'level': 'DEBUG',
        },
    }
}

#   Search directories for LESS (customizable stylesheet) files
LESS_SEARCH_PATH = [
    os.path.join(MEDIA_ROOT, 'less'),
]

MANAGERS = ADMINS

DEFAULT_HOST = SITE_INFO[1]
ALLOWED_HOSTS.append(DEFAULT_HOST)

for (key,value) in CONTACTFORM_EMAIL_CHOICES:
    if (key in ('esp','general','esp-web','relations')) and not (key in CONTACTFORM_EMAIL_ADDRESSES):
        CONTACTFORM_EMAIL_ADDRESSES[key] = DEFAULT_EMAIL_ADDRESSES[{'esp':'default','general':'default','esp-web':'support','relations':'default'}[key]]


CACHES = {
    'default': {
        'BACKEND': 'esp.utils.memcached_multikey.CacheClass',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': DEFAULT_CACHE_TIMEOUT,
    }
}

MIDDLEWARE_CLASSES = tuple([pair[1] for pair in sorted(MIDDLEWARE_GLOBAL + MIDDLEWARE_LOCAL)])

# set tempdir so that we don't have to worry about collision
if not getattr(tempfile, 'alreadytwiddled', False): # Python appears to run this multiple times
    tempdir = os.path.join(tempfile.gettempdir(), "esptmp__" + CACHE_PREFIX)
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    tempfile.tempdir = tempdir
    tempfile.alreadytwiddled = True

# change csrf cookie name from default to prevent collisions with misbehaving sites
# that set a cookie on the top-level domain
# NOTE: don't change this value; it's hard coded into various JavaScript files
CSRF_COOKIE_NAME = 'esp_csrftoken'

if SENTRY_DSN:
    # If SENTRY_DSN is set, send errors to Sentry via the Raven exception
    # handler. Note that our exception middleware (i.e., ESPErrorMiddleware)
    # will remain enabled and will receive exceptions before Raven does.
    import raven

    INSTALLED_APPS += (
        'raven.contrib.django.raven_compat',
    )
    RAVEN_CONFIG = {
        'dsn': SENTRY_DSN,
        'release': raven.fetch_git_sha(os.path.join(PROJECT_ROOT, '..')),
    }

