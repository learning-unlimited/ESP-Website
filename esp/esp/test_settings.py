"""
Test-specific settings to speed up the test suite.

- Faster password hashing (MD5) — not for production.
- In-memory cache and session backend to avoid memcached/DB.
- Disable migrations so the test DB is created from models (faster).
"""
from esp.settings import *  # noqa: F401, F403

# Faster password hashing for tests only (insecure, do not use in production)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# In-memory cache so tests don't need memcached
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Session in cache instead of DB
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'


class DisableMigrations(dict):
    """Dict proxy so MIGRATION_MODULES[app] is always None.

    Django then creates tables from models instead of running migrations,
    which is faster for the test database.
    """
    def __getitem__(self, item):
        return None

    def __contains__(self, item):
        return True
