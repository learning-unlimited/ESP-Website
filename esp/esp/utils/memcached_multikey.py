"Memcached cache backend"
from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.memcached import CacheClass as MemcacheCacheClass
from esp import settings
from esp.utils.try_multi import try_multi
import urllib

try:
    import cPickle as pickle
except:
    import pickle

FAILFAST = getattr(settings, "DEBUG", True)

# Is there any way to introspect this?
CACHE_WARNING_SIZE = 1 * 1024**2
CACHE_SIZE = 2 * 1024**2

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._wrapped_cache = MemcacheCacheClass(server, params)
        if not hasattr(settings, 'CACHE_PREFIX'):
            settings.CACHE_PREFIX = ''

    def make_key(self, key):
        return urllib.quote_plus( settings.CACHE_PREFIX + key )
    def unmake_key(self, key):
        key = urllib.unquote_plus(key)
        return key[len(settings.CACHE_PREFIX):]

    def _failfast_test(self, key, value):
        if FAILFAST:
            data_size = len(pickle.dumps(value))
            if data_size > CACHE_SIZE:
                assert False, "Data size for key '%s' too large: %d bytes" % (key, data_size)
            elif data_size > CACHE_WARNING_SIZE:
                print "Data size for key '%s' is dangerously large: %d bytes" % (key, data_size)

    @try_multi(8)
    def add(self, key, value, timeout=0):
        self._failfast_test(key, value)
        return self._wrapped_cache.add(self.make_key(key), value, timeout=timeout)

    @try_multi(8)
    def get(self, key, default=None):
        return self._wrapped_cache.get(self.make_key(key), default=default)

    @try_multi(8)
    def set(self, key, value, timeout=0):
        self._failfast_test(key, value)
        return self._wrapped_cache.set(self.make_key(key), value, timeout=timeout)

    @try_multi(8)
    def delete(self, key):
        return self._wrapped_cache.delete(self.make_key(key))

    @try_multi(8)
    def get_many(self, keys):
        wrapped_ans = self._wrapped_cache.get_many([self.make_key(key) for key in keys])
        ans = {}
        for k,v in wrapped_ans.items():
            ans[self.unmake_key(k)] = v
        return ans

    # Django 1.1 feature
    # Don't try_multi, that could be all kinds of bad...
    def incr(self, key, delta=1):
        return self._wrapped_cache.incr(self.make_key(key), delta)

    # Django 1.1 feature
    # Don't try_multi, that could be all kinds of bad...
    def decr(self, key, delta=1):
        return self._wrapped_cache.decr(self.make_key(key), delta)

    def close(self, **kwargs):
        self._wrapped_cache.close()

