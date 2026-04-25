"Memcached cache backend"

import logging
logger = logging.getLogger(__name__)

from django.core.cache.backends.base import BaseCache
import pylibmc
from django.core.cache.backends.memcached import PyLibMCCache as PylibmcCacheClass
from django.conf import settings
from esp.utils.try_multi import try_multi
from esp.utils import ascii
import hashlib
import pickle
import uuid

CACHE_WARNING_SIZE = 1 * 1024**2
DEFAULT_VALUE_CHUNK_SIZE = 900 * 1024
MAX_KEY_LENGTH = 250
NO_HASH_PREFIX = "NH_"
HASH_PREFIX = "H_"
MULTIKEY_SENTINEL = "__ESP_MULTIKEY_V1__"
MULTIKEY_META_SEPARATOR = ":"

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self._wrapped_cache = PylibmcCacheClass(server, params)
        if not hasattr(settings, 'CACHE_PREFIX'):
            settings.CACHE_PREFIX = ''
        self._value_chunk_size = getattr(settings, 'MEMCACHED_MULTIKEY_CHUNK_SIZE', DEFAULT_VALUE_CHUNK_SIZE)

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

    def _new_chunk_prefix(self, cache_key):
        unique = "%s:%s" % (cache_key, uuid.uuid4().hex)
        return "MK_" + hashlib.md5(unique.encode("UTF-8")).hexdigest()

    def _chunk_key(self, chunk_prefix, index):
        return "%s_%d" % (chunk_prefix, index)

    def _chunk_keys(self, chunk_prefix, chunk_count):
        return [self._chunk_key(chunk_prefix, i) for i in range(chunk_count)]

    def _split_value(self, value):
        serialized = pickle.dumps(value)
        if len(serialized) <= self._value_chunk_size:
            return None, None

        chunks = [serialized[i:i + self._value_chunk_size] for i in range(0, len(serialized), self._value_chunk_size)]
        return serialized, chunks

    def _encode_multikey_metadata(self, chunk_prefix, chunk_count):
        return "%s%s%s%s%d" % (
            MULTIKEY_SENTINEL,
            MULTIKEY_META_SEPARATOR,
            chunk_prefix,
            MULTIKEY_META_SEPARATOR,
            chunk_count,
        )

    def _decode_multikey_metadata(self, value):
        if not isinstance(value, str):
            return None
        if not value.startswith(MULTIKEY_SENTINEL + MULTIKEY_META_SEPARATOR):
            return None

        parts = value.split(MULTIKEY_META_SEPARATOR)
        if len(parts) != 3 or parts[0] != MULTIKEY_SENTINEL:
            return None
        try:
            chunk_count = int(parts[2])
        except (TypeError, ValueError):
            return None
        if chunk_count <= 0:
            return None
        return parts[1], chunk_count

    def _get_multikey_value(self, chunk_prefix, chunk_count, default=None, version=None):
        chunk_keys = self._chunk_keys(chunk_prefix, chunk_count)
        chunk_map = self._wrapped_cache.get_many(chunk_keys, version=version)
        return self._deserialize_chunk_map(chunk_keys, chunk_map, default=default)

    def _deserialize_chunk_map(self, chunk_keys, chunk_map, default=None):
        missing_keys = [chunk_key for chunk_key in chunk_keys if chunk_key not in chunk_map]
        if missing_keys:
            return default

        serialized = b"".join(chunk_map[chunk_key] for chunk_key in chunk_keys)
        try:
            return pickle.loads(serialized)
        except Exception:
            return default

    def _set_large_value(self, cache_key, value, timeout=None, version=None):
        serialized, chunks = self._split_value(value)
        old_metadata = self._wrapped_cache.get(cache_key, default=None, version=version)
        old_parsed = self._decode_multikey_metadata(old_metadata)

        if chunks is None:
            set_success = self._wrapped_cache.set(cache_key, value, timeout=timeout, version=version)
            if set_success and old_parsed is not None:
                old_prefix, old_count = old_parsed
                for chunk_key in self._chunk_keys(old_prefix, old_count):
                    self._wrapped_cache.delete(chunk_key, version=version)
            return set_success

        chunk_prefix = self._new_chunk_prefix(cache_key)
        chunk_keys = self._chunk_keys(chunk_prefix, len(chunks))

        written_chunk_keys = []
        for idx, chunk in enumerate(chunks):
            if not self._wrapped_cache.set(chunk_keys[idx], chunk, timeout=timeout, version=version):
                for chunk_key in written_chunk_keys:
                    self._wrapped_cache.delete(chunk_key, version=version)
                return False
            written_chunk_keys.append(chunk_keys[idx])

        metadata = self._encode_multikey_metadata(chunk_prefix, len(chunks))
        metadata_success = self._wrapped_cache.set(cache_key, metadata, timeout=timeout, version=version)
        if not metadata_success:
            for chunk_key in written_chunk_keys:
                self._wrapped_cache.delete(chunk_key, version=version)
            return False

        if old_parsed is not None:
            old_prefix, old_count = old_parsed
            for chunk_key in self._chunk_keys(old_prefix, old_count):
                self._wrapped_cache.delete(chunk_key, version=version)

        return True

    def _delete_large_value_chunks(self, cache_key, version=None):
        metadata = self._wrapped_cache.get(cache_key, default=None, version=version)
        parsed = self._decode_multikey_metadata(metadata)
        if parsed is None:
            return

        chunk_prefix, chunk_count = parsed
        for i in range(chunk_count):
            self._wrapped_cache.delete(self._chunk_key(chunk_prefix, i), version=version)

    @try_multi(8)
    def add(self, key, value, timeout=None, version=None):
        self._failfast_test(key, value)
        cache_key = self.make_key(key, version)
        serialized, chunks = self._split_value(value)
        if chunks is None:
            return self._wrapped_cache.add(cache_key, value, timeout=timeout, version=version)

        # add() is only atomic for single keys. For multikey payloads we do a
        # best-effort equivalent: if key exists, fail; otherwise store via set().
        existing = self._wrapped_cache.get(cache_key, default=None, version=version)
        if existing is not None:
            return False
        return self._set_large_value(cache_key, value, timeout=timeout, version=version)

    @try_multi(8)
    def get(self, key, default=None, version=None):
        cache_key = self.make_key(key, version)
        value = self._wrapped_cache.get(cache_key, default=default, version=version)
        parsed = self._decode_multikey_metadata(value)
        if parsed is None:
            return value
        chunk_prefix, chunk_count = parsed
        return self._get_multikey_value(chunk_prefix, chunk_count, default=default, version=version)

    @try_multi(8)
    def set(self, key, value, timeout=None, version=None):
        self._failfast_test(key, value)
        return self._set_large_value(self.make_key(key, version), value, timeout=timeout, version=version)

    @try_multi(8)
    def delete(self, key, version=None):
        cache_key = self.make_key(key, version)
        self._delete_large_value_chunks(cache_key, version=version)
        return self._wrapped_cache.delete(cache_key, version=version)

    @try_multi(8)
    def get_many(self, keys, version=None):
        key_map = dict((key, self.make_key(key, version)) for key in keys)
        wrapped_ans = self._wrapped_cache.get_many(list(key_map.values()), version=version)

        chunk_requests = {}
        all_chunk_keys = []
        ans = {}

        for key, cache_key in key_map.items():
            if cache_key not in wrapped_ans:
                continue

            value = wrapped_ans[cache_key]
            parsed = self._decode_multikey_metadata(value)
            if parsed is None:
                ans[key] = value
                continue

            chunk_prefix, chunk_count = parsed
            chunk_keys = self._chunk_keys(chunk_prefix, chunk_count)
            chunk_requests[key] = chunk_keys
            all_chunk_keys.extend(chunk_keys)

        if chunk_requests:
            chunk_map = self._wrapped_cache.get_many(all_chunk_keys, version=version)
            for key, chunk_keys in chunk_requests.items():
                value = self._deserialize_chunk_map(chunk_keys, chunk_map, default=None)
                if value is not None:
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
