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
  Email: web-team@learningu.org
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

# Auto-populated in settings.py
# Can also be overridden in local_settings.py
ALLOWED_HOSTS = []

###########################
# Default file locations  #
###########################
# Becomes concatenated with PROJECT_ROOT to form MEDIA_ROOT (see settings.py)
MEDIA_ROOT_DIR = 'public/media/'

MEDIA_URL = '/media/'

STATIC_ROOT_DIR =  'public/static/'
STATIC_URL = '/static/'

LOGIN_REDIRECT_URL = '/'

LOG_FILE = "/tmp/esp-website.log"
# Set to DEBUG for more spam or WARNING for less.  Note: setting to 'DEBUG'
# when DEBUG=True will cause every query to be logged (to the
# django.db.backends logger).
LOG_LEVEL = 'INFO'


###########################
# Default debug settings  #
###########################
DEBUG = False
SHOW_TEMPLATE_ERRORS = False
CACHE_DEBUG = False
SENTRY_DSN = ""  # (disabled)

INTERNAL_IPS = (
    '127.0.0.1',
)

##################
# Default admins #
##################
ADMINS = (
    ('LU Web Team','serverlog@learningu.org'),
)

#GRAPPELLI_ADMIN_TITLE = "ESP administration"

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
EMAIL_BACKEND = 'esp.dbmail.models.CustomSMTPBackend'

# Default addresses to send archive/bounce info to - should probably be overridden in local_settings
DEFAULT_EMAIL_ADDRESSES = {
    'archive': 'splashwebsitearchive@learningu.org',
    'bounces': 'emailbounces@learningu.org',
    'support': 'websupport@learningu.org',
    'membership': 'info@learningu.org',
    'default': 'info@learningu.org',
    'treasury': 'esp-credit-cards@mit.edu',
    'mailman_moderator': 'esp-moderators@mit.edu'
}
# The name of your host institution.
INSTITUTION_NAME = 'LearningUniversity'
# A 'slug' used in email titles, like 'ESP' or 'Splash'
ORGANIZATION_SHORT_NAME = 'Splash'
# The host for ESP site-supported email lists.
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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # Filled in by settings.py so it can depend on PROJECT_ROOT
        ],
        'OPTIONS': {
            'context_processors': [
                'esp.context_processors.media_url', # remove this one after all branches are transitioned
                'esp.context_processors.esp_user',
                'esp.context_processors.current_site',
                'esp.context_processors.index_backgrounds',
                'esp.context_processors.espuserified_request',
                'esp.context_processors.preload_images',
                'esp.context_processors.email_settings',
                'esp.context_processors.program',
                'esp.context_processors.schoolyear',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.debug',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
            ],
            'loaders': [
                'admin_tools.template_loaders.Loader',
                'esp.utils.template.Loader',
                ('django.template.loaders.cached.Loader',
                    (
                     'django.template.loaders.filesystem.Loader',
                     'django.template.loaders.app_directories.Loader',
                    )
                ),
            ]
        },
    },
]

FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

# Set MIDDLEWARE_LOCAL in local_settings.py to configure this
MIDDLEWARE_GLOBAL = [
    ( 100, 'esp.middleware.threadlocalrequest.ThreadLocals'),
   #( 100, 'django.middleware.http.SetRemoteAddrFromForwardedFor'),
    ( 300, 'esp.middleware.FixIEMiddleware'),
    ( 500, 'esp.middleware.ESPErrorMiddleware'),
    ( 700, 'django.middleware.common.CommonMiddleware'),
    ( 900, 'django.contrib.sessions.middleware.SessionMiddleware'),
    ( 950, 'django.contrib.messages.middleware.MessageMiddleware'),
    (1000, 'esp.middleware.espauthmiddleware.ESPAuthMiddleware'),
    (1050, 'django.middleware.csrf.CsrfViewMiddleware'),
    (1100, 'django.contrib.admindocs.middleware.XViewMiddleware'),
    (1250, 'esp.middleware.debugtoolbar.middleware.ESPDebugToolbarMiddleware'),
    (9000, 'esp.middleware.patchedredirect.PatchedRedirectFallbackMiddleware'),
]

ROOT_URLCONF = 'esp.urls'

APPEND_SLASH=False

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'esp.users.apps.UsersConfig',
    'esp.miniblog',
    'esp.web.apps.WebConfig',
    'esp.program.apps.ProgramConfig',
    'esp.program.modules.apps.ModulesConfig',
    'esp.dbmail',
    'esp.cal.apps.CalConfig',
    'esp.qsd',
    'esp.qsdmedia',
    'esp.resources.apps.ResourcesConfig',
    'esp.survey',
    'esp.accounting.apps.AccountingConfig',
    'esp.customforms.apps.CustomformsConfig',
    'esp.utils',    # Not a real app, but, has test cases that the test-case runner needs to find
    'esp.tagdict',
    'esp.seltests',
    'esp.themes',
    'esp.varnish',
    'argcache.apps.ArgCacheConfig',
    'django_extensions',
    'reversion',
    'form_utils',
    'django.contrib.redirects',
    'debug_toolbar',
    'esp.formstack',
    'esp.application.apps.ApplicationConfig',
    'admin_tools',
    'admin_tools.theming',
    'admin_tools.menu',
    'admin_tools.dashboard',
    'filebrowser',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.admindocs',
)

import os
for app in ('django_evolution', 'django_command_extensions'):
    if os.path.exists(app):
        INSTALLED_APPS += (app,)


SESSION_EXPIRE_AT_BROWSER_CLOSE=True

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db' #which is persistent storage

ATOMIC_REQUESTS = True

# Dotted path to callable to be used as view when a request is
# rejected by the CSRF middleware.
CSRF_FAILURE_VIEW = 'esp.web.views.csrf.csrf_failure'

# no i18n
USE_I18N = False

FORCE_SCRIPT_NAME = ''

# Page to redirect people to when they log in
# (Could be '/' for example)
DEFAULT_REDIRECT = '/myesp/redirect'

USE_MAILMAN = False
MAILMAN_PATH = '/usr/lib/mailman/bin/'

SELENIUM_PATH = os.path.join(os.path.dirname(__file__), '../../../dependencies/selenium-server-standalone-2.9.0/selenium-server-standalone-2.9.0.jar')

AUTHENTICATION_BACKENDS = (
    'esp.utils.auth_backend.ESPAuthBackend',
    )

CONTACTFORM_EMAIL_CHOICES = (
    ('esp','Unknown'),
    ('general','General'),
    ('esp-web','Website Problems'),
    ('relations',  'K-12 School Relations'),
    )

# corresponding email addresses - define these defaults in settings.py, since DEFAULT_EMAIL_ADDRESSES will be overwritten in local_settings.py
CONTACTFORM_EMAIL_ADDRESSES = {}

#   Certain media files can be served from LU's CDN.  The address of the CDN is here.
#   It can be overridden by setting CDN_ADDRESS in local_settings.py.
CDN_ADDRESS = 'https://dfwb7shzx5j05.cloudfront.net'

# allow configuration of additional Javascript to be placed on website
# configuration should include <script></script> tags
ADDITIONAL_TEMPLATE_SCRIPTS = ''

DEBUG_TOOLBAR = True # set to False in local_settings to globally disable the debug toolbar

DEBUG_TOOLBAR_PATCH_SETTINGS = False

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'esp.middleware.debugtoolbar.panels.profiling.ESPProfilingPanel',
)

def custom_show_toolbar(request):
    from esp.middleware.debugtoolbar.middleware import ESPDebugToolbarMiddleware
    return ESPDebugToolbarMiddleware.custom_show_toolbar(request)

DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': set([
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'esp.middleware.debugtoolbar.panels.profiling.ESPProfilingPanel',
    ]),
    'SHOW_TOOLBAR_CALLBACK': 'esp.settings.custom_show_toolbar',
    'EXTRA_SIGNALS': [
        'argcache.signals.cache_deleted',
    ],
    'SHOW_TEMPLATE_CONTEXT': True,
    'INSERT_BEFORE': '</div>',
    'ENABLE_STACKTRACES' : True,
    'RENDER_PANELS': None,
    'SHOW_COLLAPSED': False, # Ideally would be True, but there is a bug in their code.
}

# Settings for Stripe credit card payments (can be overridden in
# local_settings.py).  Global settings are used to define site-wide defaults,
# but the keys can be overridden in the 'stripe_settings' Tag object to direct
# payments to different accounts, either on a global or per-program basis.
STRIPE_CONFIG = {
    'secret_key': '',
    'publishable_key': '',
}

# Settings for Cybersource credit card payments. Unlike Stripe, does not support
# overrides.
CYBERSOURCE_CONFIG = {
    'post_url': '',
    'merchant_id': '',
}

FILEBROWSER_CUSTOM_ADMIN = 'esp.admin.admin_site'

#   Allow Filebrowser to edit anything under media/
#   (not just '/media/uploads/' which is the default)
FILEBROWSER_DIRECTORY = ''

FILEBROWSER_EXTENSIONS = {
    'Image': ['.jpg','.jpeg','.gif','.png','.tif','.tiff','.ico'],
    'Document': ['.pdf','.doc','.rtf','.txt','.xls','.csv'],
    'Video': ['.mov','.wmv','.mpeg','.mpg','.avi','.rm'],
    'Audio': ['.mp3','.mp4','.wav','.aiff','.midi','.m4p'],
}

FILEBROWSER_SELECT_FORMATS = {
    'file': ['Image','Document','Video','Audio'],
    'image': ['Image'],
    'document': ['Document'],
    'media': ['Video','Audio'],
}

#   Default imports for shell_plus, for convenience.
SHELL_PLUS_POST_IMPORTS = (
        ('esp.utils.shell_utils', '*'),
        )

#   Twilio configuration - should be completed in local_settings.py
TWILIO_ACCOUNT_SID = None
TWILIO_AUTH_TOKEN = None
TWILIO_ACCOUNT_NUMBERS = None

# Default configuration for themes: set this to True to make recompile_theme
# and the themes frontend refuse to do anything
LOCAL_THEME = False

ADMIN_TOOLS_MENU = 'admintoolsmenu.CustomMenu'
ADMIN_TOOLS_INDEX_DASHBOARD = 'admintoolsdash.CustomIndexDashboard'
ADMIN_TOOLS_APP_INDEX_DASHBOARD = 'admintoolsdash.CustomAppIndexDashboard'

ADMIN_TOOLS_THEMING_CSS = '/media/default_styles/admin_theme.css'
