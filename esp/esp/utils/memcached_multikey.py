"Memcached cache backend"
from django.core.cache.backends.base import BaseCache
from django.core.cache.backends.memcached import PyLibMCCache as PylibmcCacheClass
from esp import settings
from esp.utils.try_multi import try_multi
from esp.utils import ascii
import hashlib

try:
    import cPickle as pickle
except:
    import pickle

FAILFAST = getattr(settings, "DEBUG", True)

# Is there any way to introspect this?
CACHE_WARNING_SIZE = 1 * 1024**2
CACHE_SIZE = 2 * 1024**2
MAX_KEY_LENGTH = 250
NO_HASH_PREFIX = "NH_"
HASH_PREFIX = "H_"

class CacheClass(BaseCache):
    idebug = False
    queries = []

    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._wrapped_cache = PylibmcCacheClass(server, params)
        if not hasattr(settings, 'CACHE_PREFIX'):
            settings.CACHE_PREFIX = ''

    def make_key(self, key, version=None):
        rawkey = ascii( NO_HASH_PREFIX + settings.CACHE_PREFIX + key )
        django_prefix = super(CacheClass, self).make_key('', version=version)
        real_max_length = MAX_KEY_LENGTH - len(django_prefix)
        if len(rawkey) <= real_max_length:
            return rawkey
        else: # We have an oversized key; hash it
            hashkey = HASH_PREFIX + hashlib.md5(key).hexdigest()
            return hashkey + '_' + rawkey[ :  real_max_length - len(hashkey) - 1 ]

    def _failfast_test(self, key, value):
        if FAILFAST:
            data_size = len(pickle.dumps(value))
            if data_size > CACHE_SIZE:
                assert False, "Data size for key '%s' too large: %d bytes" % (key, data_size)
            elif data_size > CACHE_WARNING_SIZE:
                print "Data size for key '%s' is dangerously large: %d bytes" % (key, data_size)

    @try_multi(8)
    def add(self, key, value, timeout=0, version=None):
        self._failfast_test(key, value)
        return self._wrapped_cache.add(self.make_key(key, version), value, timeout=timeout, version=version)

    @try_multi(8)
    def get(self, key, default=None, version=None):
        val = self._wrapped_cache.get(self.make_key(key, version), default=default, version=version)
        if self.idebug: self._idebuglog("get", key, val)
        return val

    @try_multi(8)
    def set(self, key, value, timeout=0, version=None):
        self._failfast_test(key, value)
        return self._wrapped_cache.set(self.make_key(key, version), value, timeout=timeout, version=version)

    @try_multi(8)
    def delete(self, key, version=None):
        if self.idebug: self._idebuglog("delete", key, None)
        return self._wrapped_cache.delete(self.make_key(key, version), version=version)

    @try_multi(8)
    def get_many(self, keys, version=None):
        keys_dict = dict((self.make_key(key, version), key) for key in keys)
        wrapped_ans = self._wrapped_cache.get_many(keys_dict.keys(), version=version)
        ans = {}
        for k,v in wrapped_ans.items():
            ans[keys_dict[k]] = v
        return ans

    # Django 1.1 feature
    # Don't try_multi, that could be all kinds of bad...
    def incr(self, key, delta=1, version=None):
        return self._wrapped_cache.incr(self.make_key(key, version), delta, version=version)

    # Django 1.1 feature
    # Don't try_multi, that could be all kinds of bad...
    def decr(self, key, delta=1, version=None):
        return self._wrapped_cache.decr(self.make_key(key, version), delta, version=version)

    def close(self, **kwargs):
        self._wrapped_cache.close()

    def _idebuglog(self, method, key, val = None):
        if self.idebug:
            self.queries.append( {'method': method, 
                                  'key': str(key),
                                  'value': str(val) if val is not None else '' } )

    def idebug_on(self):
        self.idebug = True
        self.queries = []

    def idebug_off(self):
        self.idebug = False
        self.queries = []
