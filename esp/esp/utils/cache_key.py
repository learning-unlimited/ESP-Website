import hashlib
from django.conf import settings
from django.core.cache.backends.base import BaseCache
from esp.utils import ascii

MAX_KEY_LENGTH = 250
NO_HASH_PREFIX = "NH_"
HASH_PREFIX = "H_"

# We create a temporary BaseCache instance just to reuse Django's
# version prefix logic safely.
_base_cache = BaseCache({})

def esp_cache_key_function(key, key_prefix, version):
    """
    Replicates the old memcached_multikey.CacheClass.make_key behavior.
    """

    if not hasattr(settings, "CACHE_PREFIX"):
        settings.CACHE_PREFIX = ""

    rawkey = ascii(NO_HASH_PREFIX + settings.CACHE_PREFIX + key)

    # Django version prefix (same trick as old backend)
    django_prefix = _base_cache.make_key("", version=version)
    real_max_length = MAX_KEY_LENGTH - len(django_prefix)

    if len(rawkey) <= real_max_length:
        return rawkey
    else:
        hashkey = HASH_PREFIX + hashlib.md5(key.encode("UTF-8")).hexdigest()
        return hashkey + "_" + rawkey[: real_max_length - len(hashkey) - 1]
    