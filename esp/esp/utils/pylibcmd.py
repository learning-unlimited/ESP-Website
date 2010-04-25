"""
Thread-safe Django cache backend for pylibmc.
Tested on Python 2.6, should work on 2.5 as well.

Use it by setting CACHE_BACKEND in settings.py, e.g.:

CACHE_BACKEND = 'projdir.utils.pylibmcd://127.0.0.1:11211/'
"""
from __future__ import with_statement
from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.utils.encoding import smart_unicode, smart_str

import pylibmc

class CacheClass(BaseCache):
    def __init__(self, server, params):
        super(CacheClass, self).__init__(params)
        mc = pylibmc.Client(server.split(';'))
        mc.behaviors = {"tcp_nodelay": True}
        self._cache = mc
        self._pool = pylibmc.ThreadMappedPool(mc)

    def _call(self, method, *params):
        with self._pool.reserve() as mc:
            return getattr(mc, method)(*params)

    def add(self, key, value, timeout=None):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return self._call('add', smart_str(key), value,
                self.default_timeout if timeout is None else timeout)

    def get(self, key, default=None):
        val = self._call('get', smart_str(key))
        if val is None:
            return default
        else:
            if isinstance(val, basestring):
                return smart_unicode(val)
            else:
                return val

    def set(self, key, value, timeout=None):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._call('set', smart_str(key), value,
                self.default_timeout if timeout is None else timeout)

    def delete(self, key):
        self._call('delete', smart_str(key))

    def get_many(self, keys):
        return self._call('get_multi', map(smart_str, keys))

    def set_many(self, mapping, timeout=None):
        return self._call('set_multi',
                dict((smart_str(key), val) for key, val in mapping.iteritems()),
                self.default_timeout if timeout is None else timeout)

    def close(self, **kwargs):
        self._cache.disconnect_all()

    def incr(self, key, delta=1):
        return self._call('incr', key, delta)

    def decr(self, key, delta=1):
        return self._call('decr', key, delta)
