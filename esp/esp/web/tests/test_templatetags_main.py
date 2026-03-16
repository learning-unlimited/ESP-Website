from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.templatetags import main as web_main_tags


class MainTemplateTagHelpersTest(TestCase):
    """Unit tests for pure template tag helper functions."""

    def test_count_matching_chars(self):
        self.assertEqual(web_main_tags.count_matching_chars("/learn/cat", "/learn/catalog"), 10)
        self.assertEqual(web_main_tags.count_matching_chars("abc", "xyz"), 0)

    def test_mux_tl(self):
        self.assertEqual(web_main_tags.mux_tl("/learn/foo/bar", "teach"), "/teach/foo/bar")
        self.assertEqual(web_main_tags.mux_tl("/about/index.html", "teach"), "/about/index.html")

    def test_index(self):
        self.assertEqual(web_main_tags.index(["a", "b"], 1), "b")
        self.assertEqual(web_main_tags.index(["a", "b"], 5), "")

    def test_regexsite(self):
        self.assertEqual(web_main_tags.regexsite("learn.edu"), "learn\\.edu")

    def test_truncatewords_char(self):
        self.assertEqual(web_main_tags.truncatewords_char("alpha beta gamma", 12), " alpha beta ...")
        self.assertEqual(web_main_tags.truncatewords_char("alpha beta", "not-a-number"), "alpha beta")

    def test_as_form_label(self):
        self.assertEqual(web_main_tags.as_form_label("zip_code"), "Zip code")
