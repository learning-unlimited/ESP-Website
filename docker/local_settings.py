"""Local settings for Docker-based development."""

from __future__ import absolute_import
import os

SITE_INFO = (1, "devsite.learningu.org", "LU Dev Site")
CACHE_PREFIX = "ludev"
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
USE_MAILMAN = False
DEBUG = True
SHOW_TEMPLATE_ERRORS = DEBUG
CACHE_DEBUG = False

DATABASES = {
    "default": {
        "NAME": "devsite_django",
        "HOST": "db",
        "PORT": "5432",
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "USER": "esp",
        "PASSWORD": "esp",
    }
}

CACHES = {
    "default": {
        "BACKEND": "esp.utils.memcached_multikey.CacheClass",
        "LOCATION": "memcached:11211",
        "TIMEOUT": 86400,
    }
}

MIDDLEWARE_LOCAL = []

EMAIL_HOST_SENDER = "devsite.learningu.org"
VARNISH_HOST = None
DEBUG_TOOLBAR = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
CLOSURE_COMPILER_PATH = "/usr/lib/closure/bin"

SECRET_KEY = "docker-dev-only-secret-key"

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
