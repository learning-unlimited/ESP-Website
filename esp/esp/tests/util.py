from esp.cache.registry import dump_all_caches
from esp.web.util.structures import cross_set

from django.core.cache import cache
from django.test.testcases import TestCase
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
        
def build_posts(test_user_params = {}, test_user_joins = {}):
    """ This function will create a list of dictionaries to post to
        a web site. Useful for testing. An example using this lives in
        esp.user.tests.
    """
    
    build_posts = list()
    post_sets   = dict()

    for form, values in test_user_params.iteritems():
        tmp_list = []
        for value in values:
            tmp_list.append((form, value))
        post_sets[form] = tmp_list

    for form, values in test_user_joins.iteritems():
        tmp_list = []
        for value in values:
            tmp_list.append((form, pickle.dumps(value)))
        post_sets[form] = tmp_list

    new_post = reduce(lambda x,y:x*y,
                      [cross_set(value) for value in post_sets.values()])

    for post in new_post:
        tmp_dict = dict()
        expect_success = []

        for form, value in post:
            if type(value) == str:
                new_value = pickle.loads(value)
                if new_value[1] == False:
                    expect_success.append(form)
                tmp_dict.update(new_value[0])

            else:
                if value[1] == False:
                    expect_success.append(form)
                tmp_dict[form] = value[0]
                
        if expect_success == []:
            expect_success = True
        build_posts.append((tmp_dict, expect_success))

    return build_posts

def user_role_setup(names=['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']):
    from django.contrib.auth.models import Group
    for x in names:
        Group.objects.get_or_create(name=x)
