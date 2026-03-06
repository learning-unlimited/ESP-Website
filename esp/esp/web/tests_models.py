"""
Unit tests for esp/web/models.py

Covers:
  - NavBarCategory.get_navbars()
  - NavBarCategory.from_request()  (path-based, name-based, fallback)
  - NavBarCategory.__str__()
  - default_navbarcategory()
  - NavBarEntry.is_link()
  - NavBarEntry.makeTitle()
  - NavBarEntry.makeUrl()
  - NavBarEntry.__str__()
  - install()

PR 3/6 — esp/web module coverage improvement
"""

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.models import NavBarCategory, NavBarEntry, default_navbarcategory, install


def _make_category(name, path='', long_explanation='test'):
    return NavBarCategory.objects.create(
        name=name,
        path=path,
        long_explanation=long_explanation,
    )


def _make_entry(category, text, sort_rank=0, link=None, indent=False):
    return NavBarEntry.objects.create(
        category=category,
        text=text,
        sort_rank=sort_rank,
        link=link,
        indent=indent,
    )


# ---------------------------------------------------------------------------
# NavBarCategory.__str__
# ---------------------------------------------------------------------------

class NavBarCategoryStrTest(TestCase):

    def test_str_returns_name(self):
        cat = _make_category('home')
        self.assertEqual(str(cat), 'home')

    def test_str_with_different_name(self):
        cat = _make_category('learn')
        self.assertEqual(str(cat), 'learn')


# ---------------------------------------------------------------------------
# NavBarCategory.get_navbars()
# ---------------------------------------------------------------------------

class NavBarCategoryGetNavbarsTest(TestCase):

    def setUp(self):
        self.cat = _make_category('home')

    def test_empty_category_returns_empty_queryset(self):
        self.assertEqual(list(self.cat.get_navbars()), [])

    def test_returns_entries_for_this_category(self):
        e1 = _make_entry(self.cat, 'About', sort_rank=1)
        e2 = _make_entry(self.cat, 'Contact', sort_rank=2)
        result = list(self.cat.get_navbars())
        self.assertIn(e1, result)
        self.assertIn(e2, result)

    def test_ordered_by_sort_rank(self):
        e1 = _make_entry(self.cat, 'Third', sort_rank=30)
        e2 = _make_entry(self.cat, 'First', sort_rank=10)
        e3 = _make_entry(self.cat, 'Second', sort_rank=20)
        result = list(self.cat.get_navbars())
        self.assertEqual(result, [e2, e3, e1])

    def test_does_not_return_other_category_entries(self):
        other_cat = _make_category('other')
        _make_entry(other_cat, 'OtherEntry', sort_rank=1)
        e1 = _make_entry(self.cat, 'MyEntry', sort_rank=1)
        result = list(self.cat.get_navbars())
        self.assertEqual(result, [e1])


# ---------------------------------------------------------------------------
# NavBarCategory.from_request()
# ---------------------------------------------------------------------------

class NavBarCategoryFromRequestTest(TestCase):

    def setUp(self):
        # Ensure a default category exists for fallback
        if not NavBarCategory.objects.filter(name='default').exists():
            _make_category('default')

    def test_path_based_match(self):
        cat = _make_category('learn_splash', path='learn/splash')
        result = NavBarCategory.from_request(None, 'learn/splash/main')
        self.assertEqual(result, cat)

    def test_path_match_case_insensitive(self):
        cat = _make_category('learn_cat', path='learn/TestProgram')
        result = NavBarCategory.from_request(None, 'learn/testprogram/2024_Fall')
        self.assertEqual(result, cat)

    def test_name_based_match_when_no_path(self):
        cat = _make_category('teach')
        result = NavBarCategory.from_request('teach', None)
        self.assertEqual(result, cat)

    def test_name_based_match_with_empty_path(self):
        cat = _make_category('manage')
        result = NavBarCategory.from_request('manage', '')
        self.assertEqual(result, cat)

    def test_fallback_to_default_when_no_match(self):
        default_cat = NavBarCategory.objects.get(name='default')
        result = NavBarCategory.from_request('nonexistent_section', 'no/match/path')
        self.assertEqual(result, default_cat)

    def test_fallback_when_both_none(self):
        # Neither section nor path — should return default
        result = NavBarCategory.from_request(None, None)
        self.assertIsNotNone(result)

    def test_longer_path_takes_priority(self):
        # More specific (longer) path should win
        broad = _make_category('broad', path='learn')
        specific = _make_category('specific', path='learn/splash')
        result = NavBarCategory.from_request(None, 'learn/splash/2024')
        self.assertEqual(result, specific)


# ---------------------------------------------------------------------------
# default_navbarcategory()
# ---------------------------------------------------------------------------

class DefaultNavBarCategoryTest(TestCase):

    def setUp(self):
        # Remove cached _default so each test starts fresh
        if hasattr(NavBarCategory, '_default'):
            del NavBarCategory._default

    def test_returns_default_category(self):
        # install() already creates a 'default' category; just verify it's returned
        result = default_navbarcategory()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'default')

    def test_returns_none_when_no_categories_exist(self):
        NavBarCategory.objects.all().delete()
        if hasattr(NavBarCategory, '_default'):
            del NavBarCategory._default
        result = default_navbarcategory()
        self.assertIsNone(result)

    def test_caches_result(self):
        r1 = default_navbarcategory()
        r2 = default_navbarcategory()
        self.assertEqual(r1, r2)


# ---------------------------------------------------------------------------
# NavBarEntry.is_link()
# ---------------------------------------------------------------------------

class NavBarEntryIsLinkTest(TestCase):

    def setUp(self):
        self.cat = _make_category('home')

    def test_valid_url_returns_true(self):
        e = _make_entry(self.cat, 'Home', link='/home/')
        self.assertTrue(e.is_link())

    def test_none_link_returns_false(self):
        e = _make_entry(self.cat, 'Home', link=None)
        self.assertFalse(e.is_link())

    def test_empty_string_link_returns_false(self):
        e = _make_entry(self.cat, 'Home', link='')
        self.assertFalse(e.is_link())

    def test_whitespace_only_link_returns_true(self):
        # is_link only checks len > 0, not blank content
        e = _make_entry(self.cat, 'Home', link='   ')
        self.assertTrue(e.is_link())


# ---------------------------------------------------------------------------
# NavBarEntry.makeTitle() and makeUrl()
# ---------------------------------------------------------------------------

class NavBarEntryMakeTitleTest(TestCase):

    def setUp(self):
        self.cat = _make_category('home')

    def test_make_title_returns_text(self):
        e = _make_entry(self.cat, 'About Us', link='/about/')
        self.assertEqual(e.makeTitle(), 'About Us')

    def test_make_url_returns_link(self):
        e = _make_entry(self.cat, 'About Us', link='/about/')
        self.assertEqual(e.makeUrl(), '/about/')

    def test_make_url_none(self):
        e = _make_entry(self.cat, 'No Link', link=None)
        self.assertIsNone(e.makeUrl())


# ---------------------------------------------------------------------------
# NavBarEntry.__str__()
# ---------------------------------------------------------------------------

class NavBarEntryStrTest(TestCase):

    def setUp(self):
        self.cat = _make_category('home')

    def test_str_format(self):
        e = _make_entry(self.cat, 'About', sort_rank=5, link='/about/')
        expected = 'home:5 (About) [/about/]'
        self.assertEqual(str(e), expected)

    def test_str_with_none_link(self):
        e = _make_entry(self.cat, 'No Link', sort_rank=1, link=None)
        self.assertEqual(str(e), 'home:1 (No Link) [None]')


# ---------------------------------------------------------------------------
# install()
# ---------------------------------------------------------------------------

class InstallTest(TestCase):

    def setUp(self):
        NavBarCategory.objects.filter(name='default').delete()
        if hasattr(NavBarCategory, '_default'):
            del NavBarCategory._default

    def test_creates_default_category_if_missing(self):
        self.assertFalse(NavBarCategory.objects.filter(name='default').exists())
        install()
        self.assertTrue(NavBarCategory.objects.filter(name='default').exists())

    def test_does_not_duplicate_if_already_exists(self):
        install()
        install()
        count = NavBarCategory.objects.filter(name='default').count()
        self.assertEqual(count, 1)
