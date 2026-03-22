"""
Tests for esp/admintoolsmenu.py
Source: admintoolsmenu.py

Tests the CustomMenu class used for the Django admin interface.
Covers:
  - Initialization: correct number of children added
  - Dashboard MenuItem is present and links to the admin index
  - Bookmarks item is present
  - Applications AppList (excludes django.contrib.*)
  - Administration AppList (only django.contrib.*)
  - init_with_context delegates to super without error
"""

from django.test import RequestFactory, SimpleTestCase as TestCase
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from admin_tools.menu import items

from admintoolsmenu import CustomMenu


class CustomMenuInitTest(TestCase):
    """Tests for CustomMenu.__init__()"""

    def setUp(self):
        super().setUp()
        self.menu = CustomMenu()

    def test_init_creates_four_children(self):
        """CustomMenu should add exactly 4 items to self.children."""
        self.assertEqual(len(self.menu.children), 4)

    def test_dashboard_item_is_first(self):
        """First child should be a MenuItem (the Dashboard link)."""
        first = self.menu.children[0]
        self.assertIsInstance(first, items.MenuItem)
        self.assertEqual(first.url, reverse('admin:index'))

    def test_dashboard_item_title(self):
        """Dashboard MenuItem title should match the translated string."""
        first = self.menu.children[0]
        self.assertEqual(str(first.title), str(_('Dashboard')))

    def test_bookmarks_item_is_second(self):
        """Second child should be a Bookmarks instance."""
        second = self.menu.children[1]
        self.assertIsInstance(second, items.Bookmarks)

    def test_applications_applist_is_third(self):
        """Third child should be an AppList named 'Applications'."""
        third = self.menu.children[2]
        self.assertIsInstance(third, items.AppList)
        self.assertEqual(str(third.title), str(_('Applications')))

    def test_applications_applist_excludes_contrib(self):
        """Applications AppList should exclude django.contrib.*"""
        third = self.menu.children[2]
        self.assertIn('django.contrib.*', third.exclude)

    def test_administration_applist_is_fourth(self):
        """Fourth child should be an AppList named 'Administration'."""
        fourth = self.menu.children[3]
        self.assertIsInstance(fourth, items.AppList)
        self.assertEqual(str(fourth.title), str(_('Administration')))

    def test_administration_applist_includes_only_contrib(self):
        """Administration AppList should only include django.contrib.*"""
        fourth = self.menu.children[3]
        self.assertIn('django.contrib.*', fourth.models)


class CustomMenuInitWithContextTest(TestCase):
    """Tests for CustomMenu.init_with_context()"""

    def test_init_with_context_does_not_raise(self):
        """
        init_with_context should delegate to super() and not raise any errors.
        We pass a minimal mock context (a plain dict) since the base
        Menu.init_with_context accepts any context-like object.
        """
        menu = CustomMenu()
        factory = RequestFactory()
        request = factory.get('/')
        # admin_tools Menu.init_with_context accepts any object;
        # using a dict simulates a minimal context.
        menu.init_with_context({'request': request})