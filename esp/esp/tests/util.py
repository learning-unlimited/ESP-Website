from argcache.registry import dump_all_caches

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import TestCase, RequestFactory
import string
import random

from esp.middleware.threadlocalrequest import set_current_request, clear_current_request

class CacheFlushTestCase(TestCase):
    """ Flush the cache at the start and end of this test case """
    def setUp(self):
        super().setUp()
        # Populate the thread-local request so that get_current_request()
        # never returns None during tests.  Tests using RequestFactory bypass
        # the ThreadLocals middleware, so we prime it here instead.
        # Individual tests may call set_current_request() again with a more
        # specific request (e.g. an authenticated one) if needed.
        factory = RequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()
        request.session = self.client.session
        set_current_request(request)

    def tearDown(self):
        # Clear the thread-local after every test to avoid state leaking
        # between tests run in the same thread.
        clear_current_request()
        super().tearDown()

    def _flush_cache(self):
        """ Don't do any actual fancy deletions; just change the cache key prefix """
        if hasattr(cache, "flush_all"):
            cache.flush_all()
        else:
            # Best effort to clear out everything anyway
            try:
                dump_all_caches()
            except AttributeError:
                # Catch "AttributeError: 'NewCls' object has no attribute 'model'"
                # generated from argcache's derivedfield.py during testing
                pass
            # Rotate KEY_PREFIX to effectively invalidate all cache entries
            # (replaces old CACHE_PREFIX rotation used with memcached_multikey)
            from django.conf import settings as django_settings
            new_prefix = ''.join(random.sample(string.ascii_letters + string.digits, 16))
            django_settings.CACHES['default']['KEY_PREFIX'] = new_prefix
            cache.key_prefix = new_prefix

    def _fixture_setup(self):
        self._flush_cache()
        super()._fixture_setup()

    def _fixture_teardown(self):
        self._flush_cache()
        super()._fixture_teardown()

def user_role_setup(names=['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']):
    from django.contrib.auth.models import Group
    for x in names:
        Group.objects.get_or_create(name=x)
