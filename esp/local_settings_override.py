# Override settings to fix deploy module import
import sys
import os

# Add the parent directory to Python path to find deploy module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Now import the original settings
from esp.settings import *

# Override any settings that need local development values
DEBUG = True

# Override the database to use SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'esp', 'db.sqlite3'),
    }
}

# Override CACHES for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Empty local middleware
MIDDLEWARE_LOCAL = []
