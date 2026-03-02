from django.test import TestCase
from django.core.cache import cache
from django.conf import settings


class CacheBackendTest(TestCase):

    def test_cache_set_and_get(self):
        cache.set("unit_test_key", "value", timeout=30)
        self.assertEqual(cache.get("unit_test_key"), "value")

    def test_no_legacy_backend_used(self):
        backend = settings.CACHES["default"]["BACKEND"]
        self.assertNotIn("memcached_multikey", backend)

    def test_default_key_format(self):
        key = cache.make_key("sample")
        self.assertIn("sample", key)
