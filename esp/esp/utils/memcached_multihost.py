"""
Memcached cache backend

This cache backend maintains connections to multiple memcached backends.
It queries only the local backend, but deletes and updates information
at remote backends as well.
This allows for an array of Web machines each with a local cache that
is kept up-to-date as data changes; it is a substantial performance
optimization in the case of a read-heavy load with occasional writes
and flushes that need to take effect immediately.

The cache reads four settings from the local "settings" file:

CACHE_PREFIX
CACHE_BACKEND
REMOTE_CACHE_SERVERS
REMOTE_CACHES_TO_FLUSH

CACHE_PREFIX is a prefix string prepended to all cache keys.  It's a
means of providing some namespacing on a shared memcached server.

CACHE_BACKEND is treated the same as with the default Django Memcached
cache backend.

REMOTE_CACHE_SERVERS is a list of strings of the same format as the string
used for CACHE_BACKEND.  The servers listed here are not queried for data,
but when data is altered or deleted in the CACHE_BACKEND cache, the copy of
the data on these servers is altered or deleted as well.

REMOTE_CACHES_TO_FLUSH is a list of strings of the same format as the string
used for CACHE_BACKEND.  The servers here are not queried for data and they
do not receive data updates; instead, whenever data changes on the local
server, the corresponding keys in these servers are deleted.
This is intended for situations where you have multiple templatesets and
are caching template content (so that updated content from one server
will not be the same as updated content from another server), but you have
a shared database backend (so that a change on one server does mean that all
other servers need to regenerate their corresponding cached content).
"""

from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.memcached import PyLibMCCache as MemcacheCacheClass
from esp import settings

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)

        self._wrapped_caches = [ MemcacheCacheClass(server, params) ] + [ MemcacheCacheClass(remote_server, params) for remote_server in getattr(settings, 'REMOTE_CACHE_SERVERS', []) ]
        self._wrapped_flush_caches = [ MemcacheCacheClass(server, params) for server in getattr(settings, 'REMOTE_CACHES_TO_FLUSH', []) ]
        
        if not hasattr(settings, 'CACHE_PREFIX'):
            settings.CACHE_PREFIX = ''

    def make_key(self, key):
        """ Prefix a key with CACHE_PREFIX so that we fetch it from the proper namespace """
        return settings.CACHE_PREFIX + key
    
    def strip_key(self, key):
        """ Remove the CACHE_PREFIX prefix from a key """
        return key[len(settings.CACHE_PREFIX):]
    
    def add(self, key, value, timeout=0, version=None):
        # Update all caches that we're keeping up-to-date
        # But, don't bother doing anything to remote caches if we don't actually add anything locally
        retVal = self._wrapped_caches[0].add(self.make_key(key), value, timeout=timeout, version=version)

        if retVal:
            for wrapped_cache in self._wrapped_caches[1:]:
                wrapped_cache.add(self.make_key(key), value, timeout=timeout, version=version)

            # Delete all cache keys from caches that we're flushing on edit
            for wrapped_cache in self._wrapped_flush_caches:
                wrapped_cache.delete(self.make_key(key), version=version)

        return retVal

    def get(self, key, default=None, version=None):
        # No need to touch remote caches here
        return self._wrapped_caches[0].get(self.make_key(key), default=default, version=version)

    def set(self, key, value, timeout=0, version=None):
        # Set this key in all caches that we're keeping up-to-date
        for wrapped_cache in self._wrapped_caches:
            wrapped_cache.set(self.make_key(key), value, timeout=timeout, version=version)

        # Delete all cache keys from caches that we're flushing on edit
        for wrapped_cache in self._wrapped_flush_caches:
            wrapped_cache.delete(self.make_key(key), version=version)
        
    def delete(self, key, version=None):
        # Delete this key everywhere
        for wrapped_cache in self._wrapped_caches + self._wrapped_flush_caches:
            wrapped_cache.delete(self.make_key(key), version=version)

    def get_many(self, keys, version=None):
        # No need to touch more than one cache here, just pick one and run with it
        retDict = self._wrapped_caches[0].get_many([self.make_key(key) for key in keys], version=version)

        # Get rid of cache prefixes in the returned keys
        cleanedDict = {}
        for key, value in retDict.iteritems():
            cleanedDict[ self.strip_key(key) ] = value

        return cleanedDict

    def has_key(self, key, version=None):
        # Do we have this key locally?
        return self._wrapped_caches[0].has_key(self.make_key(key), version=version)

    def incr(self, key, delta=1, version=None):
        # Update this key in all caches that we're keeping up-to-date
        for wrapped_cache in self._wrapped_caches:
            return wrapped_cache.incr(self.make_key(key), delta, version=version)

        # Delete all cache keys from caches that we're flushing on edit
        for wrapped_cache in self._wrapped_flush_caches:
            wrapped_cache.delete(self.make_key(key), version=version)

    def decr(self, key, delta=1, version=None):
        # Update this key in all caches that we're keeping up-to-date
        for wrapped_cache in self._wrapped_caches:
            return wrapped_cache.decr(self.make_key(key), delta, version=version)

        # Delete all cache keys from caches that we're flushing on edit
        for wrapped_cache in self._wrapped_flush_caches:
            wrapped_cache.delete(self.make_key(key), version=version)        

    def __contains__(self, key):
        # Do we have this key locally?
        return self._wrapped_caches[0].__contains__(self.make_key(key))
    
    def close(self, **kwargs):
        # Close all of our cache connections
        for wrapped_cache in self._wrapped_caches + self._wrapped_flush_caches:
            wrapped_cache.close()

