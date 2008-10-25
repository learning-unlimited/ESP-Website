"Memcached cache backend"
from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.memcached import CacheClass as MemcacheCacheClass
import settings    

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._wrapped_cache = MemcacheCacheClass(server, params)        
        self._cache_prefix = getattr(settings, 'CACHE_PREFIX', '')

    def make_key(self, key):
        return self._cache_prefix + key
        
    def add(self, key, value, timeout=0):
        return self._wrapped_cache.add(self.make_key(key), value, timeout=timeout)

    def get(self, key, default=None):
        return self._wrapped_cache.get(self.make_key(key), default=default)

    def set(self, key, value, timeout=0):
        return self._wrapped_cache.set(self.make_key(key), value, timeout=timeout)

    def delete(self, key):
        return self._wrapped_cache.delete(self.make_key(key))

    def get_many(self, keys):
        return self._wrapped_cache.get_many([make_key(key) for key in self.keys])

    def close(self, **kwargs):
        self._wrapped_cache.close()

