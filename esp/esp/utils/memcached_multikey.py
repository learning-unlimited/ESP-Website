"Memcached cache backend"

import logging
logger = logging.getLogger(__name__)

import pylibmc
from django.core.cache.backends.memcached import PyLibMCCache as PylibmcCacheClass
from django.conf import settings
from esp.utils.try_multi import try_multi
from esp.utils import ascii
import hashlib
import pickle

CACHE_WARNING_SIZE = 1 * 1024**2
MAX_KEY_LENGTH = 250
NO_HASH_PREFIX = "NH_"
HASH_PREFIX = "H_"

class CacheClass(PylibmcCacheClass):
    def __init__(self, server, params):
        PylibmcCacheClass.__init__(self, server, params)
        if not hasattr(settings, 'CACHE_PREFIX'):
            settings.CACHE_PREFIX = ''

    def make_key(self, key, version=None):
        rawkey = ascii( NO_HASH_PREFIX + settings.CACHE_PREFIX + key )
        django_prefix = super().make_key('', version=version)
        real_max_length = MAX_KEY_LENGTH - len(django_prefix)
        if len(rawkey) <= real_max_length:
            return rawkey
        else: # We have an oversized key; hash it
            hashkey = HASH_PREFIX + hashlib.md5(key.encode("UTF-8")).hexdigest()
            return hashkey + '_' + rawkey[ :  real_max_length - len(hashkey) - 1 ]

    def _failfast_test(self, key, value):
        if settings.DEBUG:
            # Make a guess as to the size of the object as seen by Memcache,
            # after serializtion. This guess can be an overestimate, since some
            # backends can apply zlib compression in addition to pickling.
            try:
                data_size = len(pickle.dumps(value))
                if data_size > CACHE_WARNING_SIZE:
                    logger.warning("Data size for key '%s' is dangerously large: %d bytes", key, data_size)
            except TypeError as e:
                logger.warning("Got a TypeError (likely because value `{}` is not picklable):\n\n{}".format(value, e))

    @try_multi(8)
    def add(self, key, value, timeout=None, version=None):
        self._failfast_test(key, value)
        return super().add(key, value, timeout=timeout, version=version)

    @try_multi(8)
    def get(self, key, default=None, version=None):
        return super().get(key, default=default, version=version)

    @try_multi(8)
    def set(self, key, value, timeout=None, version=None):
        self._failfast_test(key, value)
        return super().set(key, value, timeout=timeout, version=version)

    @try_multi(8)
    def delete(self, key, version=None):
        return super().delete(key, version=version)

    @try_multi(8)
    def get_many(self, keys, version=None):
        return super().get_many(keys, version=version)
