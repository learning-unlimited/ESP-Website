from unittest.mock import patch

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.models import NavBarCategory, NavBarEntry
from esp.web.views.navBar import makeNavBar


class NavBarContextBuilderTest(TestCase):
    """Unit tests for navbar context generation."""

    def setUp(self):
        self.category = NavBarCategory.objects.create(
            name="unit-test-category",
            long_explanation="Unit test category",
        )

    def test_make_nav_bar_no_entries(self):
        context = makeNavBar(section="home", category=self.category)
        self.assertEqual(context["entries"], [])
        self.assertEqual(context["next_sort_rank"], 0)
        self.assertEqual(context["category"], self.category)

    def test_make_nav_bar_with_entries(self):
        NavBarEntry.objects.create(category=self.category, sort_rank=10, text="First", indent=False)
        NavBarEntry.objects.create(category=self.category, sort_rank=20, text="Second", indent=True)

        context = makeNavBar(section="home", category=self.category)
        self.assertEqual([x["entry"].text for x in context["entries"]], ["First", "Second"])
        self.assertEqual(context["next_sort_rank"], 30)

    def test_make_nav_bar_infers_category(self):
        with patch("esp.web.views.navBar.NavBarCategory.from_request", return_value=self.category) as from_request:
            context = makeNavBar(section="learn", path="learn/splash")

        from_request.assert_called_once_with("learn", "learn/splash")
        self.assertEqual(context["category"], self.category)
