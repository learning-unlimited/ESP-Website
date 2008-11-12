"Memcached cache backend"
from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.memcached import CacheClass as MemcacheCacheClass
from esp import settings


class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._wrapped_caches = [ MemcacheCacheClass(server, params) ] + [ MemcacheCacheClass(remote_server, params) for remote_server in getattr(settings, 'REMOTE_CACHE_SERVERS', []) ]
        if not hasattr(settings, 'CACHE_PREFIX'):
            settings.CACHE_PREFIX = ''

    def make_key(self, key):
        return settings.CACHE_PREFIX + key
        
    def add(self, key, value, timeout=0):
        for wrapped_cache in self._wrapped_caches:
            wrapped_cache.add(self.make_key(key), value, timeout=timeout)

    def get(self, key, default=None):
        return self._wrapped_caches[0].get(self.make_key(key), default=default)

    def set(self, key, value, timeout=0):
        for wrapped_cache in self._wrapped_caches:
            return wrapped_cache.set(self.make_key(key), value, timeout=timeout)

    def delete(self, key):
        for wrapped_cache in self._wrapped_caches:
            return wrapped_cache.delete(self.make_key(key))

    def get_many(self, keys):
        return self._wrapped_caches[0].get_many([make_key(key) for key in self.keys])

    def close(self, **kwargs):
        for wrapped_cache in self._wrapped_caches:
            wrapped_cache.close()

