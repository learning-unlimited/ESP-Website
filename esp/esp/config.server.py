# config file for environment-specific settings

DEBUG = {{ DEBUG }}



#                    Edit this file to override settings in                    #
#                              django_settings.py                              #

SITE_INFO = (1, 'localhost', 'DEVEL DEVEL Site')
ADMINS = (
    ('LU Web group','serverlog@lists.learningu.org'),
)
CACHE_PREFIX = "esp_webESP"

# Default addresses to send archive/bounce info to
DEFAULT_EMAIL_ADDRESSES = {
        'archive': 'learninguarchive@gmail.com',
        'bounces': 'learningubounces@gmail.com',
        'support': 'esp_web-websupport@lists.learningu.org',
        'membership': 'esp_web-websupport@lists.learningu.org',
        'default': 'esp_web-websupport@lists.learningu.org',
        }
ORGANIZATION_SHORT_NAME = 'DEVEL'
INSTITUTION_NAME = 'DEVEL'
EMAIL_HOST = 'esp_web-websupport@lists.learningu.org'

# E-mail addresses for contact form
email_choices = (
    ('general','General ESP'),
    ('esp-web','Web Site Problems'),
    ('splash','Splash!'),
    )
email_addresses = {
    'general': 'esp_web-websupport@lists.learningu.org',
    'esp-web': 'esp_web-websupport@lists.learningu.org',
    'splash': 'esp_web-websupport@lists.learningu.org',
    }
USE_MAILMAN = False
TIME_ZONE = 'America/New_York'

# File Locations
PROJECT_ROOT = '/media/sf_webapps/esp_web/esp/'
LOG_FILE = '/media/sf_webapps/logs/esp_web-django.log'

# Debug settings
DEBUG = True
DISPLAYSQL = False
TEMPLATE_DEBUG = DEBUG
SHOW_TEMPLATE_ERRORS = DEBUG
DEBUG_TOOLBAR = True # set to False to globally disable the debug toolbar

# Database
DEFAULT_CACHE_TIMEOUT = 120

DATABASE_ENGINE = 'django.db.backends.postgresql_psycopg2'
#   You can also use this database engine to improve performance at some expense
#   in error reporting capability.
#   DATABASE_ENGINE = 'esp.db.prepared'
SOUTH_DATABASE_ADAPTERS = {'default': 'south.db.postgresql_psycopg2'}
DATABASE_NAME = '{{ DB_NAME }}'
DATABASE_HOST = 'localhost'
DATABASE_PORT = '5432'
DATABASE_PASSWORD = '{{ DB_PASSWORD }}'
DATABASE_USER = '{{ DB_USER }}'
MIDDLEWARE_LOCAL = []

# E-mails for contact form
email_choices = (
    ('general', 'General Inquiries'),
    ('web',     'Web Site Problems'),
    )
# Corresponding email addresses                                                                                                                                 
email_addresses = {
    'general': 'esp_web-websupport@lists.learningu.org',
    'web':     'esp_web-websupport@lists.learningu.org',
    }

SELENIUM_TEST_RUNNER = 'esp.utils.custom_test_runner.CustomSeleniumTestRunner'
SELENIUM_DRIVERS = 'Firefox'


CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }}

SOUTH_TESTS_MIGRATE = False # To disable migrations and use syncdb instead
SKIP_SOUTH_TESTS = True # To disable South's own unit tests
import os
os.environ['REUSE_DB'] = "1"

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

TEMPLATE_LOADERS = (
    'esp.utils.template.Loader',
    # ('esp.utils.template.CachedLoader',
    #     (
         'django.template.loaders.filesystem.Loader',
         'django.template.loaders.app_directories.Loader',
    #     )
    # ),
)

