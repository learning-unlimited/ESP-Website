"""
Unit tests for RapidCheckinStudentWidget (esp/program/modules/forms/rapidcheckin.py).
"""
from unittest.mock import patch

from django.template.defaultfilters import addslashes
from django.test import SimpleTestCase, TestCase

from esp.program.modules.forms.rapidcheckin import RapidCheckinStudentWidget
from esp.users.models import ESPUser

# The widget is stateless (render() takes all its inputs as arguments and
# keeps nothing on self), so a single shared instance is safe to reuse
# across every test below instead of re-instantiating it per test class.
widget = RapidCheckinStudentWidget()


def _expected_html(name, text_value, hidden_value):
    """
    Build the exact HTML the widget is expected to produce, mirroring its
    two literal <input> templates. Used so tests assert on the full,
    precise output in one call rather than several partial assertIn checks.
    """
    return (
        '<input type="text" id="id_%s" name="%s_raw" value="%s" class="col-md-6" />'
        '<input type="hidden" id="id_%s_data" name="%s" value="%s" />'
        % (name, name, text_value, name, name, hidden_value)
    )


class RapidCheckinStudentWidgetNoDBTests(SimpleTestCase):
    """
    Cases that never reach the database: None/empty values, and values that
    fail int() conversion before any ORM lookup happens.
    """

    def test_none_value_renders_empty_inputs(self):
        html = widget.render('target_user', None)
        self.assertEqual(html, _expected_html('target_user', '', ''))

    def test_empty_string_value_renders_empty_inputs(self):
        html = widget.render('target_user', '')
        self.assertEqual(html, _expected_html('target_user', '', ''))

    def test_non_numeric_value_handled_gracefully(self):
        """
        A non-numeric value fails int() before any database lookup, so this
        must not raise and must fall back to empty inputs.
        """
        html = widget.render('target_user', 'not-a-number')
        self.assertEqual(html, _expected_html('target_user', '', ''))


class RapidCheckinStudentWidgetDBTests(TestCase):
    """
    Cases that reach ESPUser.objects.get(), so a real database is required:
    a stale/nonexistent numeric pk, a pk for a user that does exist, and
    escaping of special characters in that user's rendered representation.
    """

    def setUp(self):
        self.user = ESPUser.objects.create_user(
            username='rapidcheckin_test_student', password='password', email='student@test.org')

    def test_nonexistent_pk_handled_gracefully(self):
        """
        A numeric value that doesn't correspond to any user should raise
        ESPUser.DoesNotExist internally and fall back to empty inputs,
        not propagate the exception.
        """
        missing_pk = self.user.pk + 999999
        html = widget.render('target_user', str(missing_pk))
        self.assertEqual(html, _expected_html('target_user', '', ''))

    def test_existing_user_pk_renders_data(self):
        with patch.object(ESPUser, 'ajax_str', return_value='Some User'):
            html = widget.render('target_user', str(self.user.pk))
        expected_text_value = addslashes('Some User (%s)' % self.user.pk)
        self.assertEqual(
            html, _expected_html('target_user', expected_text_value, str(self.user.pk)))

    def test_special_characters_in_ajax_str_are_escaped(self):
        """
        ajax_str() renders arbitrary user-controlled text (e.g. a name).
        If it contains quotes, they must be escaped via addslashes so the
        value="..." attribute isn't broken out of.
        """
        with patch.object(ESPUser, 'ajax_str', return_value='Weird "Name"'):
            html = widget.render('target_user', str(self.user.pk))
        expected_text_value = addslashes('Weird "Name" (%s)' % self.user.pk)
        self.assertEqual(
            html, _expected_html('target_user', expected_text_value, str(self.user.pk)))
        # The raw, unescaped quote must not appear in the attribute value.
        self.assertNotIn('value="Weird "Name" (%s)"' % self.user.pk, html)
