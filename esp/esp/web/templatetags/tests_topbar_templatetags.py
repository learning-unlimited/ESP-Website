"""
Unit tests for esp/web/templatetags/topbar.py

Covers get_primary_nav() for:
  - contexts without a request, and paths outside the known nav links
  - level 2 pages (e.g. /myesp/home/) and level 3 pages (e.g. /learn/catalog)
  - the extra admin/onsite nav links
  - the memcached round trip used for admin+onsite users

cache_inclusion_tag leaves the undecorated function bound to the module name
(it only attaches a .cached_function attribute), so get_primary_nav can be
called directly with a plain dict context.

The user objects below are stubs rather than ESPUsers because get_primary_nav
only ever calls isAdmin() and isOnsite() on them; stubbing keeps these tests
focused on the nav logic and off the group machinery, which is tested
elsewhere.
"""

from django.core.cache import cache

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.templatetags import topbar


class StubRequest(object):
    def __init__(self, path):
        self.path = path


class StubUser(object):
    def __init__(self, is_admin=False, is_onsite=False):
        self._is_admin = is_admin
        self._is_onsite = is_onsite

    def isAdmin(self):
        return self._is_admin

    def isOnsite(self):
        return self._is_onsite


def make_context(path, is_admin=False, is_onsite=False):
    return {
        'user': StubUser(is_admin=is_admin, is_onsite=is_onsite),
        'request': StubRequest(path),
    }


class GetPrimaryNavEmptyResultTest(TestCase):

    def test_missing_request_returns_empty_dict(self):
        self.assertEqual(topbar.get_primary_nav({'user': StubUser()}), {})

    def test_unknown_top_level_path_returns_empty_dict(self):
        self.assertEqual(topbar.get_primary_nav(make_context('/unknown/path/')), {})

    def test_known_navlink_without_a_section_returns_user_only(self):
        # 'contactinfo' is a known nav link, but no section is served out of a
        # /contactinfo/ URL prefix, so neither the level 2 nor the level 3
        # branch applies and no page_setup is built.
        result = topbar.get_primary_nav(make_context('/contactinfo/thing/'))

        self.assertEqual(list(result.keys()), ['user'])


class GetPrimaryNavLevel2Test(TestCase):

    def setUp(self):
        super().setUp()
        self.context = make_context('/myesp/home/')
        self.result = topbar.get_primary_nav(self.context)
        self.page_setup = self.result['page_setup']

    def test_button_location_and_stylesheet(self):
        self.assertEqual(self.page_setup['buttonlocation'], 'lev2')
        self.assertEqual(self.page_setup['stylesheet'], 'myesp2')

    def test_page_section_written_back_to_context(self):
        self.assertEqual(self.context['page_section']['id'], 'myesp/lev2')
        self.assertEqual(self.page_setup['section']['id'], 'myesp/lev2')

    def test_only_the_current_section_is_highlighted(self):
        highlighted = [x['id'] for x in self.page_setup['navlinks'] if x['highlight']]
        self.assertEqual(highlighted, ['myesp'])

    def test_navlinks_cover_the_basic_sections(self):
        self.assertEqual(
            [x['id'] for x in self.page_setup['navlinks']],
            topbar.basic_navlinks,
        )

    def test_admin_and_onsite_links_appended_for_privileged_users(self):
        result = topbar.get_primary_nav(
            make_context('/myesp/home/', is_admin=True, is_onsite=True))

        ids = [x['id'] for x in result['page_setup']['navlinks']]
        self.assertEqual(ids[-2:], ['admin', 'onsite'])


class GetPrimaryNavLevel3Test(TestCase):

    def setUp(self):
        super().setUp()
        self.context = make_context('/learn/catalog')
        self.result = topbar.get_primary_nav(self.context)
        self.page_setup = self.result['page_setup']

    def test_stylesheet_and_page_section(self):
        self.assertEqual(self.page_setup['stylesheet'], 'takeaclass3')
        self.assertEqual(self.context['page_section']['id'], 'takeaclass/lev3')
        self.assertEqual(self.page_setup['section']['cursection'], 'takeaclass')

    def test_only_the_current_section_is_highlighted(self):
        highlighted = [x['id'] for x in self.page_setup['navlinks'] if x['highlight']]
        self.assertEqual(highlighted, ['takeaclass'])

    def test_related_sections_get_a_nested_button_location(self):
        buttonlocs = {x['id']: x['buttonloc'] for x in self.page_setup['navlinks']}

        # Sections listed as related to takeaclass render inside its sub-bar.
        self.assertEqual(buttonlocs['volunteertoteach'], 'takeaclass/lev3')
        self.assertEqual(buttonlocs['getinvolved'], 'takeaclass/lev3')
        # Everything else stays on the top-level bar.
        self.assertEqual(buttonlocs['takeaclass'], 'lev3')
        self.assertEqual(buttonlocs['discoveresp'], 'lev3')

    def test_admin_and_onsite_links_are_never_highlighted(self):
        result = topbar.get_primary_nav(
            make_context('/learn/catalog', is_admin=True, is_onsite=True))

        extras = [x for x in result['page_setup']['navlinks']
                  if x['id'] in ('admin', 'onsite')]
        self.assertEqual(len(extras), 2)
        for link in extras:
            self.assertFalse(link['highlight'])
            self.assertEqual(link['buttonloc'], 'lev2')


class GetPrimaryNavCachingTest(TestCase):
    """
    page_setup is only cached for users who are both admin and onsite, since
    those are the only requests that get a cache key.
    """

    path = '/myesp/home/'
    # urlencode() is urllib's quote(), which treats '/' as safe, so the path
    # goes into the key unescaped.
    cache_key = 'NAVBAR__/myesp/home/'

    def setUp(self):
        super().setUp()
        # get_primary_nav caches under a fixed key in the default cache, which
        # Django does not reset between tests.
        cache.delete(self.cache_key)

    def tearDown(self):
        cache.delete(self.cache_key)
        super().tearDown()

    def test_admin_onsite_result_is_written_to_the_cache(self):
        result = topbar.get_primary_nav(
            make_context(self.path, is_admin=True, is_onsite=True))

        self.assertEqual(cache.get(self.cache_key), result['page_setup'])

    def test_cached_page_setup_is_reused(self):
        cache.set(self.cache_key, {'stylesheet': 'from-cache'}, 99999)

        result = topbar.get_primary_nav(
            make_context(self.path, is_admin=True, is_onsite=True))

        self.assertEqual(result['page_setup'], {'stylesheet': 'from-cache'})

    def test_unprivileged_result_is_not_cached(self):
        topbar.get_primary_nav(make_context(self.path))

        self.assertIsNone(cache.get(self.cache_key))
