"Memcached cache backend"

import logging
logger = logging.getLogger(__name__)

from django.core.cache.backends.base import BaseCache, DEFAULT_TIMEOUT
from django.core.cache.backends.memcached import PyMemcacheCache as PymemcacheCacheClass
from django.conf import settings
from esp.utils.try_multi import try_multi
from esp.utils import ascii
import hashlib
import pickle

CACHE_WARNING_SIZE = 1 * 1024**2
DEFAULT_VALUE_CHUNK_SIZE = 900 * 1024
DEFAULT_MAX_CHUNKS = 16
# Chunks are never written without an expiry. This is the expiry used when the
# configured CACHES timeout resolves to "never expire"; see _chunk_timeout.
DEFAULT_CHUNK_ORPHAN_TTL = 24 * 60 * 60
MAX_KEY_LENGTH = 250
NO_HASH_PREFIX = "NH_"
HASH_PREFIX = "H_"
CHUNK_PREFIX = "MK_"
MULTIKEY_SENTINEL = "__ESP_MULTIKEY_V1__"
MULTIKEY_META_SEPARATOR = ":"

_MISSING = object()

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._wrapped_cache = PymemcacheCacheClass(server, params)
        if not hasattr(settings, 'CACHE_PREFIX'):
            settings.CACHE_PREFIX = ''
        self._value_chunk_size = getattr(settings, 'MEMCACHED_MULTIKEY_CHUNK_SIZE', DEFAULT_VALUE_CHUNK_SIZE)
        self._max_chunks = getattr(settings, 'MEMCACHED_MULTIKEY_MAX_CHUNKS', DEFAULT_MAX_CHUNKS)
        self._chunk_orphan_ttl = getattr(settings, 'MEMCACHED_MULTIKEY_CHUNK_TTL', DEFAULT_CHUNK_ORPHAN_TTL)

    def make_key(self, key, version=None):
        rawkey = ascii( NO_HASH_PREFIX + settings.CACHE_PREFIX + key )
        django_prefix = super().make_key('', version=version)
        real_max_length = MAX_KEY_LENGTH - len(django_prefix)
        if len(rawkey) <= real_max_length:
            return rawkey
        else: # We have an oversized key; hash it
            hashkey = HASH_PREFIX + hashlib.sha256(key.encode("UTF-8")).hexdigest()
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

    def _chunk_prefix(self, cache_key):
        """
        Chunk keys are derived from the cache key alone, so re-writing a large
        value overwrites its chunks in place.
        """
        return CHUNK_PREFIX + hashlib.sha256(cache_key.encode("UTF-8")).hexdigest()[:32]

    def _chunk_key(self, chunk_prefix, index):
        return "%s_%d" % (chunk_prefix, index)

    def _chunk_keys(self, chunk_prefix, chunk_count):
        return [self._chunk_key(chunk_prefix, i) for i in range(chunk_count)]

    def _digest(self, serialized):
        return hashlib.sha256(serialized).hexdigest()[:32]

    def _split_value(self, value):
        """
        Return (serialized_bytes, chunks).  chunks is None when the value fits
        in a single memcached item.
        """
        serialized = pickle.dumps(value)
        if len(serialized) <= self._value_chunk_size:
            return serialized, None

        chunks = [serialized[i:i + self._value_chunk_size] for i in range(0, len(serialized), self._value_chunk_size)]
        return serialized, chunks

    def _encode_multikey_metadata(self, chunk_count, digest):
        return "%s%s%d%s%s" % (
            MULTIKEY_SENTINEL,
            MULTIKEY_META_SEPARATOR,
            chunk_count,
            MULTIKEY_META_SEPARATOR,
            digest,
        )

    def _is_multikey_metadata(self, value):
        return isinstance(value, str) and value.startswith(MULTIKEY_SENTINEL + MULTIKEY_META_SEPARATOR)

    def _decode_multikey_metadata(self, value):
        if not self._is_multikey_metadata(value):
            return None

        parts = value.split(MULTIKEY_META_SEPARATOR)
        if len(parts) != 3:
            return None
        try:
            chunk_count = int(parts[1])
        except (TypeError, ValueError):
            return None
        if chunk_count <= 0 or not parts[2]:
            return None
        return chunk_count, parts[2]

    def _resolve_metadata(self, cache_key, value, default=_MISSING, version=None):
        """
        Turn a value read from the metadata key into the real cached value.
        """
        parsed = self._decode_multikey_metadata(value)
        if parsed is None:
            logger.warning("Cache key '%s' holds unparseable multikey metadata; treating as a cache miss.", cache_key)
            return default

        chunk_count, digest = parsed
        chunk_keys = self._chunk_keys(self._chunk_prefix(cache_key), chunk_count)
        chunk_map = self._wrapped_get_many(chunk_keys, version=version)
        return self._deserialize_chunk_map(cache_key, chunk_keys, digest, chunk_map, default=default)

    def _deserialize_chunk_map(self, cache_key, chunk_keys, digest, chunk_map, default=_MISSING):
        missing_keys = [chunk_key for chunk_key in chunk_keys if chunk_key not in chunk_map]
        if missing_keys:
            # Memcached evicts items independently, so a large value survives
            # only as long as all of its chunks do.
            logger.warning("Cache key '%s' resolved to %d chunks but %d are missing (likely evicted); "
                           "treating as a cache miss.", cache_key, len(chunk_keys), len(missing_keys))
            return default

        try:
            serialized = b"".join(chunk_map[chunk_key] for chunk_key in chunk_keys)
        except TypeError:
            logger.warning("Cache key '%s' has non-bytes chunk data; treating as a cache miss.", cache_key)
            return default

        if self._digest(serialized) != digest:
            # Either a concurrent writer replaced some chunks while we were
            # reading, or a partially-failed write left a mix of old and new
            # chunks behind.  Either way the payload is not trustworthy.
            logger.warning("Cache key '%s' failed its chunk digest check (torn read or partial write); "
                           "treating as a cache miss.", cache_key)
            return default

        try:
            return pickle.loads(serialized)
        except Exception:
            logger.warning("Cache key '%s' could not be unpickled from %d chunks; treating as a cache miss.",
                           cache_key, len(chunk_keys), exc_info=True)
            return default

    def _chunk_timeout(self, timeout):
        """
        Resolve the caller's timeout for chunk writes.
        """
        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout
        return self._chunk_orphan_ttl if timeout is None else timeout

    def _set_large_value(self, cache_key, value, timeout=DEFAULT_TIMEOUT, version=None):
        """
        Note that none of the writes below check a return value, because there
        is nothing to check: Django's BaseMemcachedCache.set returns None
        whether it succeeded or not.  All it does on failure is delete the key,
        so a failed write leaves the key empty rather than stale.
        """
        serialized, chunks = self._split_value(value)

        if chunks is None:
            # Any chunks left behind by a previous large value at this key are
            # now unreachable, because the metadata key that pointed at them is
            # what we are overwriting here.  They expire on their own.
            self._wrapped_cache.set(cache_key, value, timeout=timeout, version=version)
            return True

        if len(chunks) > self._max_chunks:
            # Refuse rather than let one runaway value evict the whole cache.
            # This restores the pre-chunking behaviour ("too big to cache") for
            # pathological values only.
            logger.warning("Refusing to cache key '%s': %d bytes would need %d chunks (max %d). "
                           "Raise MEMCACHED_MULTIKEY_MAX_CHUNKS if this is expected.",
                           cache_key, len(serialized), len(chunks), self._max_chunks)
            return False

        # Chunks always get a bounded expiry, even when the caller asked for
        # none.
        chunk_timeout = self._chunk_timeout(timeout)

        chunk_prefix = self._chunk_prefix(cache_key)
        for index, chunk in enumerate(chunks):
            self._wrapped_cache.set(self._chunk_key(chunk_prefix, index), chunk,
                                    timeout=chunk_timeout, version=version)

        # If this write fails, Django has already deleted the key, so the key is
        # left empty rather than holding either the new or the previous value.
        metadata = self._encode_multikey_metadata(len(chunks), self._digest(serialized))
        self._wrapped_cache.set(cache_key, metadata, timeout=timeout, version=version)
        return True

    @try_multi(8)
    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        self._failfast_test(key, value)
        cache_key = self.make_key(key, version)
        _, chunks = self._split_value(value)
        if chunks is None:
            return self._wrapped_cache.add(cache_key, value, timeout=timeout, version=version)

        # add() is only atomic for single keys. For multikey payloads we do a
        # best-effort equivalent: if key exists, fail; otherwise store via set().
        existing = self._wrapped_get(cache_key, default=None, version=version)
        if existing is not None:
            return False
        return self._set_large_value(cache_key, value, timeout=timeout, version=version)

    def _wrapped_get(self, cache_key, default=None, version=None):
        """
        Read a single key, tolerating an unreadable stored value.

        Unpickling happens inside the wrapped backend, so a value written by a
        different Python or referring to a class that has since been renamed or
        moved raises here.
        """
        try:
            return self._wrapped_cache.get(cache_key, default=default, version=version)
        except Exception:
            logger.warning("Cache key '%s' could not be read (unreadable stored value); "
                           "treating as a cache miss.", cache_key, exc_info=True)
            return default

    def _wrapped_get_many(self, cache_keys, version=None):
        """Bulk counterpart to _wrapped_get; see there for why this is guarded."""
        try:
            return self._wrapped_cache.get_many(cache_keys, version=version)
        except Exception:
            logger.warning("Bulk cache read of %d keys failed (unreadable stored value); "
                           "treating all as cache misses.", len(cache_keys), exc_info=True)
            return {}

    @try_multi(8)
    def get(self, key, default=None, version=None):
        cache_key = self.make_key(key, version)
        value = self._wrapped_get(cache_key, default=default, version=version)
        if not self._is_multikey_metadata(value):
            return value
        return self._resolve_metadata(cache_key, value, default=default, version=version)

    @try_multi(8)
    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        self._failfast_test(key, value)
        return self._set_large_value(self.make_key(key, version), value, timeout=timeout, version=version)

    @try_multi(8)
    def delete(self, key, version=None):
        # Deleting the metadata key is enough.
        return self._wrapped_cache.delete(self.make_key(key, version), version=version)

    @try_multi(8)
    def get_many(self, keys, version=None):
        key_map = dict((key, self.make_key(key, version)) for key in keys)
        wrapped_ans = self._wrapped_get_many(list(key_map.values()), version=version)

        chunk_requests = {}
        all_chunk_keys = []
        ans = {}

        for key, cache_key in key_map.items():
            if cache_key not in wrapped_ans:
                continue

            value = wrapped_ans[cache_key]
            if not self._is_multikey_metadata(value):
                ans[key] = value
                continue

            parsed = self._decode_multikey_metadata(value)
            if parsed is None:
                logger.warning("Cache key '%s' holds unparseable multikey metadata; treating as a cache miss.",
                               cache_key)
                continue

            chunk_count, digest = parsed
            chunk_keys = self._chunk_keys(self._chunk_prefix(cache_key), chunk_count)
            chunk_requests[key] = (cache_key, chunk_keys, digest)
            all_chunk_keys.extend(chunk_keys)

        if chunk_requests:
            chunk_map = self._wrapped_get_many(all_chunk_keys, version=version)
            for key, (cache_key, chunk_keys, digest) in chunk_requests.items():
                value = self._deserialize_chunk_map(cache_key, chunk_keys, digest, chunk_map, default=_MISSING)
                if value is not _MISSING:
                    ans[key] = value

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
