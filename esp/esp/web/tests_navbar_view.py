"""
Unit tests for esp/web/views/navBar.py

Covers:
  - makeNavBar() with an explicit category (entry ordering, next_sort_rank,
    section pass-through)
  - makeNavBar() falling back to NavBarCategory.from_request() when no
    category is supplied
"""

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.models import NavBarCategory, NavBarEntry
from esp.web.views.navBar import makeNavBar


class MakeNavBarTest(TestCase):

    def setUp(self):
        self.category = NavBarCategory.objects.create(
            name='navbar-view-test',
            path='navbarviewtest',
            long_explanation='Category used by makeNavBar tests.',
        )

    def test_no_entries(self):
        context = makeNavBar(section='home', category=self.category)

        self.assertEqual(context['entries'], [])
        self.assertEqual(context['category'], self.category)
        self.assertEqual(context['section'], 'home')
        # An empty category starts numbering at zero rather than at 10.
        self.assertEqual(context['next_sort_rank'], 0)

    def test_entries_are_sorted_by_rank(self):
        NavBarEntry.objects.create(
            category=self.category, sort_rank=20, text='Second', indent=True)
        NavBarEntry.objects.create(
            category=self.category, sort_rank=10, text='First', indent=False)

        context = makeNavBar(section='home', category=self.category)

        self.assertEqual(
            [x['entry'].text for x in context['entries']], ['First', 'Second'])
        self.assertEqual(context['next_sort_rank'], 30)

    def test_entries_of_other_categories_are_excluded(self):
        other = NavBarCategory.objects.create(
            name='navbar-view-other',
            path='navbarviewother',
            long_explanation='Unrelated category.',
        )
        NavBarEntry.objects.create(
            category=self.category, sort_rank=10, text='Mine', indent=False)
        NavBarEntry.objects.create(
            category=other, sort_rank=10, text='Theirs', indent=False)

        context = makeNavBar(section='home', category=self.category)

        self.assertEqual([x['entry'].text for x in context['entries']], ['Mine'])

    def test_category_inferred_from_path(self):
        context = makeNavBar(section='learn', path='navbarviewtest/splash')

        self.assertEqual(context['category'], self.category)

    def test_category_inferred_from_section_name(self):
        context = makeNavBar(section='navbar-view-test')

        self.assertEqual(context['category'], self.category)
