""" Django settings for ESP website. """
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
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
    ('ESP Webmasters','esp-serverlog@mit.edu'),
    ('David Meyer',   'pdox@alum.mit.edu'),
    ('LU Webmasters', 'serverlog@lists.learningu.org'),
    ('J.D. Zamfirescu', 'zamfire+esperrors@gmail.com'),
)


##########################
# Default email settings #
##########################
EMAIL_HOST   = 'localhost'
EMAIL_PORT   = '25'
SERVER_EMAIL = 'server@stanfordesp.org'
EMAIL_SUBJECT_PREFIX = '[ ESP ERROR ] '

# Default addresses to send archive/bounce info to
DEFAULT_EMAIL_ADDRESSES = {
    'archive': 'esparchive@gmail.com',
    'bounces': 'esp-bounces@mit.edu'
}


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
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

# Set MIDDLEWARE_LOCAL in local_settings.py to configure this
MIDDLEWARE_GLOBAL = [
   #( 100, 'django.middleware.http.SetRemoteAddrFromForwardedFor'),
   #( 200, 'esp.queue.middleware.QueueMiddleware'),
    ( 300, 'esp.middleware.FixIEMiddleware'),
    ( 500, 'esp.middleware.ESPErrorMiddleware'),
   #( 600, 'esp.middleware.psycomiddleware.PsycoMiddleware'),
    ( 700, 'django.middleware.common.CommonMiddleware'),
   #( 800, 'esp.middleware.esp_sessions.SessionMiddleware'),  # DEPRECATED -- Relies on mem_db, which is currently nonfunctional
    ( 900, 'django.contrib.sessions.middleware.SessionMiddleware'),
    (1000, 'esp.middleware.ESPAuthMiddleware'),
    (1100, 'django.middleware.doc.XViewMiddleware'),
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
    'esp.setup',
    'esp.qsd',
    'esp.qsdmedia',
    'esp.money',
    'esp.resources',
    'esp.gen_media',
    'esp.dblog',
    'esp.membership',
    'esp.queue',
    'esp.survey',
    'esp.accounting_core',
    'esp.accounting_docs',
    'esp.shortterm',
    'esp.utils',    # Not a real app, but, has test cases that the test-case runner needs to find
    'esp.cache',
    'esp.cache_loader',
#    'django_evolution',
    'django_extensions',
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
                               'esp.context_processors.espuserified_request',
                               'esp.context_processors.preload_images',
                               'django.core.context_processors.i18n',
                               'django.core.context_processors.auth',
                               'django.core.context_processors.media',
                               )

# no i18n
USE_I18N = False

AUTH_PROFILE_MODULE='users.ESPUser_Profile'

FORCE_SCRIPT_NAME = ''
