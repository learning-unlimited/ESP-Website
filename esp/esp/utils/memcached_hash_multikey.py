from django.core.cache.backends.base import BaseCache
from esp.utils.memcache_multikey import CacheClass as MemcacheMultikeyCacheClass

class CacheClass(MemcacheMultikeyCacheClass):
    def make_key(self, key):
        return sha.sha( MemcacheMultikeyCacheClass.make_key(self, key) ).hexdigest()
