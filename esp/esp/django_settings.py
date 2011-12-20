""" Django settings for ESP website. """
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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
  Email: web-team@lists.learningu.org
"""

################################################################################
#                                                                              #
#                           DO NOT MODIFY THIS FILE                            #
#                       Edit local_settings.py instead                         #
#                                                                              #
################################################################################


###############################################
# Default site identification                 #
#  you really don't want to leave this as is. #
###############################################

SITE_INFO = (1, 'esp.mit.edu', 'Main ESP Site')

# Must be unique for every site hosted
CACHE_PREFIX="ESP"


###########################
# Default file locations  #
###########################
# Becomes concatenated with PROJECT_ROOT to form MEDIA_ROOT (see settings.py)
MEDIA_ROOT_DIR = 'public/media/'

MEDIA_URL = '/media/'

ADMIN_MEDIA_PREFIX = '/media/admin/'

LOGIN_REDIRECT_URL = '/'


###########################
# Default debug settings  #
###########################
DEBUG = False
DISPLAYSQL = False
TEMPLATE_DEBUG = False
SHOW_TEMPLATE_ERRORS = False
CACHE_DEBUG = False

INTERNAL_IPS = (
    '127.0.0.1',
)

##################
# Default admins #
##################
ADMINS = (
    ('LU Web Team','serverlog@lists.learningu.org'),
)

#############################
# Default database settings #
#############################

# The name, user and password must be filled in via local_settings.py and django_settings.py
DATABASES = {'default':
    {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '',
        'HOST': 'localhost',
        'PORT': '5432',
        'USER': '',
        'PASSWORD': '',
    }
}

##########################
# Default email settings #
##########################
EMAIL_HOST   = 'localhost'
EMAIL_PORT   = '25'
SERVER_EMAIL = 'server@diogenes.learningu.org'
EMAIL_SUBJECT_PREFIX = '[ ESP ERROR ] '
EMAIL_HOST_SENDER = EMAIL_HOST

# Default addresses to send archive/bounce info to - should probably be overridden in local_settings
DEFAULT_EMAIL_ADDRESSES = {
    'archive': 'learninguarchive@gmail.com',
    'bounces': 'learningubounces@gmail.com',
    'support': 'websupport@lists.learningu.org',
    'membership': 'info@learningu.org',
    'default': 'info@learningu.org',
}
# The name of your host institution.
INSTITUTION_NAME = 'MIT'
# A 'slug' used in e-mail titles, like 'ESP' or 'Splash'
ORGANIZATION_SHORT_NAME = 'ESP'
# The host for ESP site-supported e-mail lists.
EMAIL_HOST = 'localhost'

#################################
# Default localization settings #
#################################
TIME_ZONE = 'America/New_York'

LANGUAGE_CODE = 'en-us'


################################################################################
#                                                                              #
#        You probably don't want to override anything past this point.         #
#                                                                              #
################################################################################

# Default cache timeout in seconds
DEFAULT_CACHE_TIMEOUT = 86400

SITE_ID = 1

TEMPLATE_LOADERS = (
    'esp.utils.template.Loader',
    ('django.template.loaders.cached.Loader',
        (
         'django.template.loaders.filesystem.Loader',
         'django.template.loaders.app_directories.Loader',
        )
    ),
)

# Set MIDDLEWARE_LOCAL in local_settings.py to configure this
MIDDLEWARE_GLOBAL = [
    ( 100, 'esp.middleware.threadlocalrequest.ThreadLocals'),
   #( 100, 'django.middleware.http.SetRemoteAddrFromForwardedFor'),
   #( 200, 'esp.queue.middleware.QueueMiddleware'),
    ( 300, 'esp.middleware.FixIEMiddleware'),
    ( 500, 'esp.middleware.ESPErrorMiddleware'),
   #( 600, 'esp.middleware.psycomiddleware.PsycoMiddleware'),
    ( 700, 'django.middleware.common.CommonMiddleware'),
   #( 800, 'esp.middleware.esp_sessions.SessionMiddleware'),  # DEPRECATED -- Relies on mem_db, which is currently nonfunctional
    ( 900, 'django.contrib.sessions.middleware.SessionMiddleware'),
    (1000, 'esp.middleware.espauthmiddleware.ESPAuthMiddleware'),
    (1050, 'django.middleware.csrf.CsrfViewMiddleware'),
    (1100, 'django.middleware.doc.XViewMiddleware'),
   #es
    #(1150, 'sslauth.middleware.SSLAuthMiddleware'),
    (1200, 'django.middleware.gzip.GZipMiddleware'),
    (1300, 'esp.middleware.PrettyErrorEmailMiddleware'),
    (1400, 'esp.middleware.StripWhitespaceMiddleware'),
    (1500, 'django.middleware.transaction.TransactionMiddleware'),
    (1600, 'esp.datatree.middleware.DataTreeLockMiddleware'),
]

ROOT_URLCONF = 'esp.urls'

APPEND_SLASH=False

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'esp.datatree',
    'esp.users',
    'esp.membership',
    'esp.miniblog',
    'esp.web',
    'esp.program',
    'esp.program.modules',
    'esp.dbmail',
    'esp.cal',
    'esp.lib',
    'esp.qsd',
    'esp.qsdmedia',
    'esp.resources',
    'esp.gen_media',
    'esp.dblog',
    'esp.membership',
    'esp.queue',
    'esp.survey',
    'esp.accounting_core',
    'esp.accounting_docs',
    'esp.shortterm',
    'esp.customforms',
    'esp.utils',    # Not a real app, but, has test cases that the test-case runner needs to find
    'esp.cache',
    'esp.cache_loader',
    'esp.tagdict',
    'django_extensions',
    'reversion',
    'south',
    'sslauth',
    'form_utils',
    'esp.seltests',
    'esp.dataviews',
)

import os
for app in ('django_evolution', 'django_command_extensions'):
    if os.path.exists(app):
        INSTALLED_APPS += (app,)


SESSION_EXPIRE_AT_BROWSER_CLOSE=True

SESSION_ENGINE="django.contrib.sessions.backends.cached_db"

TEMPLATE_CONTEXT_PROCESSORS = ('esp.context_processors.media_url', # remove this one after all branches are transitioned
                               'esp.context_processors.esp_user',
                               'esp.context_processors.current_site',
                               'esp.context_processors.index_backgrounds',
                               #'esp.context_processors.espuserified_request',
                               'esp.context_processors.preload_images',
                               'django.core.context_processors.i18n',
                               #'django.contrib.auth.context_processors.auth',
                               'django.core.context_processors.media',
                               )

# no i18n
USE_I18N = False

AUTH_PROFILE_MODULE='users.ESPUser_Profile'

FORCE_SCRIPT_NAME = ''

# Page to redirect people to when they log in
# (Could be '/' for example)
DEFAULT_REDIRECT = '/myesp/redirect'

USE_MAILMAN = False
MAILMAN_PATH = '/usr/lib/mailman/bin/'

TEST_RUNNER = 'esp.utils.custom_test_runner.CustomSeleniumTestRunner'

SELENIUM_PATH = os.path.join(os.path.dirname(__file__), '../../../dependencies/selenium-server-standalone-2.9.0/selenium-server-standalone-2.9.0.jar')

if False:
    import logging
    logging.basicConfig(
        level = logging.DEBUG,
        format = '%(asctime)s %(levelname)s %(message)s',
        filename = '/tmp/mit-esp.log',
        filemode = 'w'
    )


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'sslauth.backends.SSLAuthBackend',
    )

SSLAUTH_USE_COOKIE = True
SSLAUTH_CREATE_USER = True

try:
    from esp.utils.sslauth_create_user import find_ssl_user    
except ImportError:
    ## Django hasn't done its sys.path-hacking yet at this point
    from utils.sslauth_create_user import find_ssl_user
SSLAUTH_CREATE_USERNAME_CALLBACK = find_ssl_user



email_choices = (
    ('esp','Unknown'),
    ('general','General ESP'),
    ('esp-web','Web Site Problems'),
    ('relations',  'K-12 School Relations'),
    )

# corresponding email addresses                                                                                                                                                     
email_addresses = {
    'esp'     : DEFAULT_EMAIL_ADDRESSES['default'],
    'general'     : DEFAULT_EMAIL_ADDRESSES['default'],
    'esp-web' : DEFAULT_EMAIL_ADDRESSES['support'],
    'relations': DEFAULT_EMAIL_ADDRESSES['default'],
    }

VARNISH_HOST = "localhost"
VARNISH_PORT = 8000
