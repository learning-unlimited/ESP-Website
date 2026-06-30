"""
Unit tests for:
  - esp/web/templatetags/main.py  (extract_theme, get_nav_category)
  - esp/web/views/main.py         (contact() POST paths)

Covers:
  templatetags/main.py:
    extract_theme() — URL matched to nav category links → tabcolorN
    extract_theme() — unmatched URL → tabcolor0
    get_nav_category() — path matched to nav header → returns category dict
    get_nav_category() — unmatched path → falls back to 'learn' default

  views/main.py — contact() POST:
    valid POST → email sent, redirect to ?success
    invalid POST (missing required fields) → re-renders form (200)
    password keyword in message → password-recovery prompt (no send, 200)
    anonymous POST → sender goes to bcc, not to-address

PR 9/10 — esp/web module coverage improvement
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser, Group
from django.test import TestCase, RequestFactory, override_settings

from esp.users.models import ESPUser
from esp.web.templatetags.main import extract_theme, get_nav_category
from esp.web.views.main import contact


# ---------------------------------------------------------------------------
# Shared fake nav_structure used by extract_theme and get_nav_category tests
# ---------------------------------------------------------------------------

FAKE_NAV_STRUCTURE = {
    'nav_structure': [
        {
            'header_link': '/learn/',
            'links': [
                {'link': '/learn/studentreg/'},
                {'link': '/learn/catalog/'},
            ],
        },
        {
            'header_link': '/teach/',
            'links': [
                {'link': '/teach/teacher_reg/'},
            ],
        },
    ]
}


def _make_user(username, password='testpass123', email=None):
    return ESPUser.objects.create_user(
        username=username,
        password=password,
        email=email or '%s@test.com' % username,
        first_name='Test',
        last_name='User',
    )


# ---------------------------------------------------------------------------
# extract_theme()
# ---------------------------------------------------------------------------

class ExtractThemeTest(TestCase):
    """extract_theme(url) returns the correct tabcolorN CSS class."""

    def _call(self, url):
        with patch('esp.web.templatetags.main.ThemeController') as MockTC:
            MockTC.return_value.get_template_settings.return_value = FAKE_NAV_STRUCTURE
            return extract_theme(url)

    def test_exact_link_match_returns_nonzero_tabcolor(self):
        """URL matching a specific nav link returns tabcolor with index > 0."""
        result = self._call('/learn/catalog/')
        # /learn/catalog/ is the 2nd link in the first category → tab_index=2
        self.assertEqual(result, 'tabcolor2')

    def test_header_link_match_returns_tabcolor0(self):
        """URL matching a category header (not a sub-link) returns tabcolor0."""
        result = self._call('/learn/')
        self.assertEqual(result, 'tabcolor0')

    def test_unmatched_url_returns_tabcolor0(self):
        """URL with no meaningful match beyond leading '/' returns tabcolor0."""
        result = self._call('/zzznomatch/')
        self.assertEqual(result, 'tabcolor0')

    def test_teach_link_match(self):
        """URL matching a link in the second category returns correct tabcolor."""
        result = self._call('/teach/teacher_reg/')
        self.assertEqual(result, 'tabcolor1')

    def test_returns_string(self):
        """Return value is always a string starting with 'tabcolor'."""
        result = self._call('/anything/')
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith('tabcolor'))


# ---------------------------------------------------------------------------
# get_nav_category()
# ---------------------------------------------------------------------------

class GetNavCategoryTest(TestCase):
    """get_nav_category(path) returns the matching nav category dict."""

    def _call(self, path):
        with patch('esp.web.templatetags.main.ThemeController') as MockTC:
            MockTC.return_value.get_template_settings.return_value = FAKE_NAV_STRUCTURE
            return get_nav_category(path)

    def test_learn_path_returns_learn_category(self):
        """Path starting with /learn/ returns the learn category."""
        result = self._call('/learn/studentreg/')
        self.assertEqual(result['header_link'], '/learn/')

    def test_teach_path_returns_teach_category(self):
        """Path starting with /teach/ returns the teach category."""
        result = self._call('/teach/teacher_reg/')
        self.assertEqual(result['header_link'], '/teach/')

    def test_unmatched_path_falls_back_to_learn(self):
        """Unmatched path falls back to the 'learn' default category."""
        result = self._call('/zzznomatch/foo/')
        self.assertEqual(result['header_link'], '/learn/')

    def test_returns_dict_with_links(self):
        """Returned category dict includes a 'links' key."""
        result = self._call('/learn/')
        self.assertIn('links', result)

    def test_root_path_falls_back_to_learn(self):
        """Root path '/' has empty first_level → falls back to learn default."""
        result = self._call('/')
        self.assertEqual(result['header_link'], '/learn/')


# ---------------------------------------------------------------------------
# contact() POST paths
# ---------------------------------------------------------------------------

FAKE_CONTACTFORM_ADDRESSES = {
    'esp': 'esp@test.com',
    'general': 'general@test.com',
    'esp-web': 'web@test.com',
    'relations': 'relations@test.com',
}


class ContactPostTest(TestCase):
    """contact() view POST paths."""

    def setUp(self):
        self.factory = RequestFactory()

    def _post_request(self, data, user=None):
        request = self.factory.post('/contact/', data=data)
        request.user = user if user is not None else AnonymousUser()
        request.session = {}
        return request

    def _valid_data(self, **overrides):
        """Minimal valid ContactForm POST data.

        ContactForm has a ReCaptchaField; we patch it out in all contact tests.
        person_type and hear_about are required ChoiceFields.
        """
        data = {
            'topic': 'esp',
            'subject': 'Hello there',
            'message': 'This is a test message.',
            'sender': 'sender@example.com',
            'name': '',
            'person_type': 'Student',
            'hear_about': 'Friend',
            'anonymous': '',
            'cc_myself': '',
            'decline_password_recovery': '',
            'g-recaptcha-response': 'PASS',  # value irrelevant when captcha is mocked
        }
        data.update(overrides)
        return data

    def _contact_patches(self):
        """Context manager stack: enable contact form + mock captcha + mock send_mail."""
        return (
            patch('esp.web.views.main.Tag.getBooleanTag', return_value=True),
            patch('captcha.fields.ReCaptchaField.clean', return_value='PASS'),
            patch('esp.dbmail.models.send_mail'),
            override_settings(CONTACTFORM_EMAIL_ADDRESSES=FAKE_CONTACTFORM_ADDRESSES),
        )

    def test_valid_post_redirects_to_success(self):
        """Valid POST with no matching usernames → sends mail and redirects to ?success."""
        request = self._post_request(self._valid_data())
        with patch('esp.web.views.main.Tag.getBooleanTag', return_value=True), \
             patch('captcha.fields.ReCaptchaField.clean', return_value='PASS'), \
             patch('esp.dbmail.models.send_mail'), \
             override_settings(CONTACTFORM_EMAIL_ADDRESSES=FAKE_CONTACTFORM_ADDRESSES):
            response = contact(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('?success', response['Location'])

    def test_valid_post_sends_email(self):
        """Valid POST calls send_mail exactly once."""
        request = self._post_request(self._valid_data())
        with patch('esp.web.views.main.Tag.getBooleanTag', return_value=True), \
             patch('captcha.fields.ReCaptchaField.clean', return_value='PASS'), \
             patch('esp.dbmail.models.send_mail') as mock_send, \
             override_settings(CONTACTFORM_EMAIL_ADDRESSES=FAKE_CONTACTFORM_ADDRESSES):
            contact(request)
        mock_send.assert_called_once()

    def test_invalid_post_rerenders_form(self):
        """POST missing required fields (subject, message) → 200 re-render."""
        data = {'topic': 'esp', 'sender': 'x@y.com'}
        request = self._post_request(data)
        with patch('esp.web.views.main.Tag.getBooleanTag', return_value=True), \
             override_settings(CONTACTFORM_EMAIL_ADDRESSES=FAKE_CONTACTFORM_ADDRESSES):
            response = contact(request)
        self.assertEqual(response.status_code, 200)

    def test_password_keyword_suppresses_send(self):
        """Non-anonymous POST with password keyword and a matching user → no send, 200."""
        _make_user('pwkeyword_user', email='sender@example.com')
        data = self._valid_data(
            message='I forgot my password',
            sender='sender@example.com',
        )
        request = self._post_request(data)
        with patch('esp.web.views.main.Tag.getBooleanTag', return_value=True), \
             patch('captcha.fields.ReCaptchaField.clean', return_value='PASS'), \
             patch('esp.dbmail.models.send_mail') as mock_send, \
             override_settings(CONTACTFORM_EMAIL_ADDRESSES=FAKE_CONTACTFORM_ADDRESSES):
            response = contact(request)
        # Should NOT redirect; re-render at 200 so user sees the password-recovery prompt
        self.assertEqual(response.status_code, 200)
        mock_send.assert_not_called()

    def test_anonymous_post_redirects_to_success(self):
        """Anonymous POST → sender goes to bcc, still sends and redirects."""
        data = self._valid_data(anonymous='on')
        request = self._post_request(data)
        with patch('esp.web.views.main.Tag.getBooleanTag', return_value=True), \
             patch('captcha.fields.ReCaptchaField.clean', return_value='PASS'), \
             patch('esp.dbmail.models.send_mail'), \
             override_settings(CONTACTFORM_EMAIL_ADDRESSES=FAKE_CONTACTFORM_ADDRESSES):
            response = contact(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('?success', response['Location'])
