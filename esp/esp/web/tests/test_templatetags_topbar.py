from unittest.mock import patch

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.templatetags import topbar


class DummyRequest:
    def __init__(self, path):
        self.path = path


class DummyUser:
    def __init__(self, is_admin=False, is_onsite=False):
        self._is_admin = is_admin
        self._is_onsite = is_onsite

    def isAdmin(self):
        return self._is_admin

    def isOnsite(self):
        return self._is_onsite


class TopbarTemplateTagTest(TestCase):
    def test_missing_request_returns_empty_dict(self):
        context = {"user": DummyUser()}
        self.assertEqual(topbar.get_primary_nav(context), {})

    def test_unknown_path_returns_empty_dict(self):
        context = {
            "user": DummyUser(),
            "request": DummyRequest("/unknown/path/"),
        }
        self.assertEqual(topbar.get_primary_nav(context), {})

    def test_level2_navigation_context(self):
        context = {
            "user": DummyUser(),
            "request": DummyRequest("/myesp/home/"),
        }

        result = topbar.get_primary_nav(context)

        self.assertIn("page_setup", result)
        self.assertEqual(result["page_setup"]["buttonlocation"], "lev2")
        self.assertEqual(result["page_setup"]["stylesheet"], "myesp2")
        self.assertEqual(context["page_section"]["id"], "myesp/lev2")

    def test_level3_navigation_context(self):
        context = {
            "user": DummyUser(),
            "request": DummyRequest("/learn/catalog"),
        }

        result = topbar.get_primary_nav(context)

        self.assertIn("page_setup", result)
        self.assertEqual(result["page_setup"]["stylesheet"], "takeaclass3")
        self.assertEqual(context["page_section"]["id"], "takeaclass/lev3")

    def test_cached_page_setup_for_admin_onsite_user(self):
        context = {
            "user": DummyUser(is_admin=True, is_onsite=True),
            "request": DummyRequest("/myesp/home/"),
        }

        with patch(
            "esp.web.templatetags.topbar.cache.get",
            return_value={"cached": True},
        ) as cache_get:
            result = topbar.get_primary_nav(context)

        cache_get.assert_called_once()
        self.assertEqual(result["page_setup"], {"cached": True})
