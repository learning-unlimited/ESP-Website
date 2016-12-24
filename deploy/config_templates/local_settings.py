""" Local chapter-specific settings. """

SITE_INFO = (1, <%= @hostname.inspect %>, <%= @hostlabel.inspect %>)
ADMINS = (
    ("LU Web group","serverlog@learningu.org"),
)
CACHE_PREFIX = <%= @cache_prefix.inspect %>

DEFAULT_EMAIL_ADDRESSES = {
    "archive": "learninguarchive@gmail.com",
    "bounces": "learningubounces@gmail.com",
    "support": <%= @email.inspect %>,
    "membership": <%= @email.inspect %>,
    "default": <%= @email.inspect %>,
}

ORGANIZATION_SHORT_NAME = <%= @shortname.inspect %>
INSTITUTION_NAME = <%= @institution.inspect %>
EMAIL_HOST = <%= @emailhost.inspect %>
EMAIL_PORT = <%= @emailport.to_i.inspect %>
EMAIL_USE_TLS = <%= @emailport == 587 ? 'True' : 'False' %>
EMAIL_USE_SSL = <%= @emailport == 465 ? 'True' : 'False' %>
EMAIL_HOST_USER = <%= @emailuser.inspect %>
EMAIL_HOST_PASSWORD = <%= @emailpass.inspect %>
EMAIL_HOST_SENDER = <%= @hostname.inspect %>

USE_MAILMAN = False
TIME_ZONE = <%= @timezone.inspect %>

# File Locations
PROJECT_ROOT = <%= @project_root.inspect %>

# Debug settings
DEBUG = False
SHOW_TEMPLATE_ERRORS = DEBUG
DEBUG_TOOLBAR = True # set to False to globally disable the debug toolbar

# Database
DEFAULT_CACHE_TIMEOUT = 120
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": <%= @dbhost.inspect %>,
        "PORT": <%= @dbport.inspect %>,
        "USER": <%= @dbuser.inspect %>,
        "PASSWORD": <%= @dbpass.inspect %>,
        "NAME": <%= @dbname.inspect %>,
    },
}

MIDDLEWARE_LOCAL = []

SECRET_KEY = <%= @secret_key.inspect %>
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
ALLOWED_HOSTS = [<%= @hostname.inspect %>]

DEBUG = True # TODO: remove me

<%= local_settings_extra %>
