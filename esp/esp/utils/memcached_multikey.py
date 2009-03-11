"Memcached cache backend"
from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.memcached import CacheClass as MemcacheCacheClass
from esp import settings

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._wrapped_cache = MemcacheCacheClass(server, params)
        if not hasattr(settings, 'CACHE_PREFIX'):
            settings.CACHE_PREFIX = ''

    def make_key(self, key):
        return settings.CACHE_PREFIX + key
    def unmake_key(self, key):
        return key[len(settings.CACHE_PREFIX):]
        
    def add(self, key, value, timeout=0):
        return self._wrapped_cache.add(self.make_key(key), value, timeout=timeout)

    def get(self, key, default=None):
        return self._wrapped_cache.get(self.make_key(key), default=default)

    def set(self, key, value, timeout=0):
        return self._wrapped_cache.set(self.make_key(key), value, timeout=timeout)

    def delete(self, key):
        return self._wrapped_cache.delete(self.make_key(key))

    def get_many(self, keys):
        wrapped_ans = self._wrapped_cache.get_many([self.make_key(key) for key in keys])
        ans = {}
        for k,v in wrapped_ans.items():
            ans[self.unmake_key(k)] = v
        return ans

    def close(self, **kwargs):
        self._wrapped_cache.close()

