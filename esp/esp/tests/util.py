from argcache.registry import dump_all_caches

from django.core.cache import cache
from django.test import TestCase
import pickle
import string
import random

class CacheFlushTestCase(TestCase):
    """ Flush the cache at the start and end of this test case """
    def _flush_cache(self):
        """ Don't do any actual fancy deletions; just change the cache prefix """
        if hasattr(cache, "flush_all"):
            cache.flush_all()
        else:
            # Best effort to clear out everything anyway
            dump_all_caches()

            from esp import settings
            settings.CACHE_PREFIX = ''.join( random.sample( string.letters + string.digits, 16 ) )
            from django.conf import settings as django_settings
            django_settings.CACHE_PREFIX = settings.CACHE_PREFIX

    def _fixture_setup(self):
        self._flush_cache()
        super(CacheFlushTestCase, self)._fixture_setup()

    def _fixture_teardown(self):
        self._flush_cache()
        super(CacheFlushTestCase, self)._fixture_teardown()

def user_role_setup(names=['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']):
    from django.contrib.auth.models import Group
    for x in names:
        Group.objects.get_or_create(name=x)
