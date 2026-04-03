"""
Test-specific settings to speed up the test suite.

- Faster password hashing (MD5) — not for production.
- In-memory cache (LocMemCache) to avoid memcached dependency.
- DB-backed sessions (avoids depending on cache backend semantics).

Note: DisableMigrations was tried but breaks argcache's dynamic model
classes (NewCls) and data migrations that populate RecordType fixtures.
DummyCache was considered but breaks cache-dependent tests (e.g.
TagTest::testTagCaching which expects zero queries after caching).
"""
from esp.settings import *  # noqa: F401, F403

# Faster password hashing for tests only (insecure, do not use in production)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# In-memory cache so tests don't need memcached.
# LocMemCache is preferred over DummyCache because DummyCache never stores
# anything, which breaks tests that rely on cache behaviour (e.g. tag caching).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Use DB-backed sessions for tests (avoids depending on cache backend semantics)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
