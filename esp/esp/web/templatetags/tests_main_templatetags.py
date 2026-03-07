"""
Unit tests for esp/web/templatetags/main.py

Covers all template filters and helper functions:
  count_matching_chars, mux_tl, split, index, concat,
  equal, notequal, bool_or, bool_and, get_field,
  regexsite, truncatewords_char, as_form_label
"""

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.web.templatetags.main import (
    count_matching_chars,
    mux_tl,
    split,
    index,
    concat,
    equal,
    notequal,
    bool_or,
    bool_and,
    get_field,
    regexsite,
    truncatewords_char,
    as_form_label,
)


class CountMatchingCharsTest(TestCase):
    """Tests for count_matching_chars helper."""

    def test_identical_strings(self):
        self.assertEqual(count_matching_chars("abc", "abc"), 3)

    def test_no_common_prefix(self):
        self.assertEqual(count_matching_chars("abc", "xyz"), 0)

    def test_partial_match(self):
        self.assertEqual(count_matching_chars("/learn/foo", "/learn/bar"), 7)

    def test_str1_shorter(self):
        # str1 is shorter than str2; result is len(str1)
        self.assertEqual(count_matching_chars("ab", "abcd"), 2)

    def test_str2_shorter(self):
        # str2 is shorter than str1; result is len(str2)
        self.assertEqual(count_matching_chars("abcd", "ab"), 2)

    def test_empty_strings(self):
        self.assertEqual(count_matching_chars("", ""), 0)

    def test_one_empty(self):
        self.assertEqual(count_matching_chars("", "abc"), 0)
        self.assertEqual(count_matching_chars("abc", ""), 0)


class MuxTlTest(TestCase):
    """Tests for mux_tl filter — swaps the top-level segment of a URL."""

    def test_learn_swapped(self):
        self.assertEqual(mux_tl("/learn/foo/bar/index.html", "teach"),
                         "/teach/foo/bar/index.html")

    def test_teach_swapped(self):
        self.assertEqual(mux_tl("/teach/foo/bar", "learn"),
                         "/learn/foo/bar")

    def test_manage_swapped(self):
        self.assertEqual(mux_tl("/manage/prog/inst", "onsite"),
                         "/onsite/prog/inst")

    def test_onsite_swapped(self):
        self.assertEqual(mux_tl("/onsite/prog/inst", "manage"),
                         "/manage/prog/inst")

    def test_volunteer_swapped(self):
        self.assertEqual(mux_tl("/volunteer/prog/inst", "learn"),
                         "/learn/prog/inst")

    def test_non_tl_url_returned_unchanged(self):
        self.assertEqual(mux_tl("/contact/us", "teach"), "/contact/us")

    def test_no_leading_slash_returned_unchanged(self):
        # splitstr[0] != "" → return as-is
        self.assertEqual(mux_tl("learn/foo", "teach"), "learn/foo")

    def test_short_path_returned_unchanged(self):
        self.assertEqual(mux_tl("/", "teach"), "/")


class SplitFilterTest(TestCase):
    """Tests for split filter."""

    def test_split_on_comma(self):
        self.assertEqual(split("a,b,c", ","), ["a", "b", "c"])

    def test_split_on_space(self):
        self.assertEqual(split("hello world", " "), ["hello", "world"])

    def test_no_separator_present(self):
        self.assertEqual(split("abc", ","), ["abc"])

    def test_empty_string(self):
        self.assertEqual(split("", ","), [""])


class IndexFilterTest(TestCase):
    """Tests for index filter."""

    def test_valid_index(self):
        self.assertEqual(index(["a", "b", "c"], 1), "b")

    def test_first_element(self):
        self.assertEqual(index(["x", "y"], 0), "x")

    def test_out_of_range_returns_empty(self):
        self.assertEqual(index(["a", "b"], 10), "")

    def test_negative_index(self):
        # Python allows negative indexing; -1 returns last element
        self.assertEqual(index(["a", "b", "c"], -1), "c")


class ConcatFilterTest(TestCase):
    """Tests for concat filter."""

    def test_basic_concat(self):
        self.assertEqual(concat("hello", " world"), "hello world")

    def test_concat_empty_string(self):
        self.assertEqual(concat("hello", ""), "hello")

    def test_concat_to_empty(self):
        self.assertEqual(concat("", "world"), "world")


class EqualFilterTest(TestCase):
    """Tests for equal filter."""

    def test_equal_strings(self):
        self.assertTrue(equal("abc", "abc"))

    def test_unequal_strings(self):
        self.assertFalse(equal("abc", "xyz"))

    def test_equal_ints(self):
        self.assertTrue(equal(42, 42))

    def test_unequal_ints(self):
        self.assertFalse(equal(1, 2))

    def test_equal_none(self):
        self.assertTrue(equal(None, None))


class NotEqualFilterTest(TestCase):
    """Tests for notequal filter."""

    def test_not_equal_strings(self):
        self.assertTrue(notequal("abc", "xyz"))

    def test_equal_strings_returns_false(self):
        self.assertFalse(notequal("abc", "abc"))

    def test_not_equal_ints(self):
        self.assertTrue(notequal(1, 2))


class BoolOrFilterTest(TestCase):
    """Tests for bool_or filter."""

    def test_both_true(self):
        self.assertTrue(bool_or(True, True))

    def test_first_true(self):
        self.assertTrue(bool_or(True, False))

    def test_second_true(self):
        self.assertTrue(bool_or(False, True))

    def test_both_false(self):
        self.assertFalse(bool_or(False, False))

    def test_truthy_values(self):
        self.assertEqual(bool_or("hello", ""), "hello")

    def test_falsy_first(self):
        self.assertEqual(bool_or("", "fallback"), "fallback")


class BoolAndFilterTest(TestCase):
    """Tests for bool_and filter."""

    def test_both_true(self):
        self.assertTrue(bool_and(True, True))

    def test_first_false(self):
        self.assertFalse(bool_and(False, True))

    def test_second_false(self):
        self.assertFalse(bool_and(True, False))

    def test_both_false(self):
        self.assertFalse(bool_and(False, False))

    def test_truthy_strings(self):
        self.assertEqual(bool_and("hello", "world"), "world")

    def test_falsy_first_string(self):
        self.assertEqual(bool_and("", "world"), "")


class GetFieldFilterTest(TestCase):
    """Tests for get_field filter."""

    def test_returns_attribute(self):
        class Obj:
            name = "ESP"
        self.assertEqual(get_field(Obj(), "name"), "ESP")

    def test_returns_method_result(self):
        class Obj:
            value = 42
        self.assertEqual(get_field(Obj(), "value"), 42)


class RegexSiteFilterTest(TestCase):
    """Tests for regexsite filter."""

    def test_dot_escaped(self):
        self.assertEqual(regexsite("mit.edu"), r"mit\.edu")

    def test_multiple_dots(self):
        self.assertEqual(regexsite("www.mit.edu"), r"www\.mit\.edu")

    def test_no_dots(self):
        self.assertEqual(regexsite("nodots"), "nodots")

    def test_empty_string(self):
        self.assertEqual(regexsite(""), "")


class TruncatewordsCharTest(TestCase):
    """Tests for truncatewords_char filter."""

    def test_short_string_not_truncated(self):
        # "hello" is 5 chars; limit 20 → no truncation
        result = truncatewords_char("hello world", 50)
        self.assertNotIn("...", result)

    def test_long_string_truncated(self):
        result = truncatewords_char("one two three four five", 10)
        self.assertIn("...", result)

    def test_truncated_result_within_limit(self):
        result = truncatewords_char("one two three four five six seven", 15)
        # strip leading space from result
        self.assertLessEqual(len(result.strip()), 20)

    def test_invalid_arg_returns_original(self):
        original = "hello world"
        result = truncatewords_char(original, "notanumber")
        self.assertEqual(result, original)

    def test_empty_string(self):
        result = truncatewords_char("", 10)
        self.assertEqual(result.strip(), "")


class AsFormLabelTest(TestCase):
    """Tests for as_form_label filter."""

    def test_underscores_replaced(self):
        self.assertEqual(as_form_label("first_name"), "First name")

    def test_first_letter_capitalised(self):
        self.assertEqual(as_form_label("email"), "Email")

    def test_multiple_underscores(self):
        self.assertEqual(as_form_label("zip_postal_code"), "Zip postal code")

    def test_already_capitalised(self):
        self.assertEqual(as_form_label("Name"), "Name")

    def test_empty_string(self):
        self.assertEqual(as_form_label(""), "")
