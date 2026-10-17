"""
Unit tests for:
  - esp/web/templatetags/main.py: extract_theme(), get_nav_category()
  - esp/web/views/main.py: contact() POST paths

Closes #4810.
"""

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser
from esp.web.templatetags.main import extract_theme, get_nav_category
from esp.web.views.main import contact


# ---------------------------------------------------------------------------
# Navigation fixtures
# ---------------------------------------------------------------------------

FAKE_NAV_STRUCTURE = {
    'nav_structure': [
        {
            'header_link': '/learn/',
            'links': [
                {'link': '/learn/studentreg/'},
                {'link': '/learn/classes/'},
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


# ---------------------------------------------------------------------------
# extract_theme()
# ---------------------------------------------------------------------------

class ExtractThemeTest(TestCase):
    """extract_theme(url) returns the matching tab color scheme based on nav_structure."""

    def _call(self, url):
        with patch('esp.web.templatetags.main.ThemeController') as mock_tc:
            mock_tc.return_value.get_template_settings.return_value = FAKE_NAV_STRUCTURE
            return extract_theme(url)

    def test_sub_link_match_first_item_returns_tabcolor1(self):
        """URL matching the first link in a category returns tabcolor1."""
        self.assertEqual(self._call('/learn/studentreg/'), 'tabcolor1')

    def test_sub_link_match_second_item_returns_tabcolor2(self):
        """URL matching the second link in a category returns tabcolor2."""
        self.assertEqual(self._call('/learn/classes/'), 'tabcolor2')

    def test_header_link_match_returns_tabcolor0(self):
        """URL matching a category header (not a sub-link) returns tabcolor0."""
        self.assertEqual(self._call('/learn/'), 'tabcolor0')

    def test_different_category_match_returns_correct_tabcolor(self):
        """URL matching a link in another category returns correct tabcolor."""
        self.assertEqual(self._call('/teach/teacher_reg/'), 'tabcolor1')

    def test_unmatched_url_returns_tabcolor0(self):
        """URL with no matching navigation entry falls back to tabcolor0."""
        self.assertEqual(self._call('/nomatch/'), 'tabcolor0')


# ---------------------------------------------------------------------------
# get_nav_category()
# ---------------------------------------------------------------------------

class GetNavCategoryTest(TestCase):
    """get_nav_category(path) returns the matching category dict from nav_structure."""

    def _call(self, path):
        with patch('esp.web.templatetags.main.ThemeController') as mock_tc:
            mock_tc.return_value.get_template_settings.return_value = FAKE_NAV_STRUCTURE
            return get_nav_category(path)

    def test_matching_first_level_returns_category(self):
        """Path starting with /learn/ matches the learn category."""
        result = self._call('/learn/studentreg/')
        self.assertEqual(result['header_link'], '/learn/')

    def test_matching_different_category(self):
        """Path starting with /teach/ matches the teach category."""
        result = self._call('/teach/teacher_reg/')
        self.assertEqual(result['header_link'], '/teach/')

    def test_unmatched_path_falls_back_to_learn(self):
        """Unmatched path falls back to the default 'learn' category."""
        result = self._call('/zzznomatch/foo/')
        self.assertEqual(result['header_link'], '/learn/')

    def test_root_path_returns_first_matching_category(self):
        """Root path '/' has an empty first segment matching header_link."""
        result = self._call('/')
        self.assertEqual(result['header_link'], '/learn/')


# ---------------------------------------------------------------------------
# contact() POST paths
# ---------------------------------------------------------------------------

FAKE_CONTACTFORM_ADDRESSES = {
    'esp': 'esp@example.com',
    'general': 'general@example.com',
}


@override_settings(CONTACTFORM_EMAIL_ADDRESSES=FAKE_CONTACTFORM_ADDRESSES)
class ContactPostTest(TestCase):
    """contact() view POST paths."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

        # Enable contact form via Tag
        patcher_tag = patch('esp.web.views.main.Tag.getBooleanTag', return_value=True)
        self.mock_tag = patcher_tag.start()
        self.addCleanup(patcher_tag.stop)

        # Bypass real CAPTCHA validation across all contact form tests
        patcher_captcha = patch('captcha.fields.ReCaptchaField.clean', return_value='PASS')
        self.mock_captcha = patcher_captcha.start()
        self.addCleanup(patcher_captcha.stop)

        # Mock send_mail to prevent real emails and inspect arguments
        patcher_mail = patch('esp.dbmail.models.send_mail')
        self.mock_send_mail = patcher_mail.start()
        self.addCleanup(patcher_mail.stop)

    def _post_request(self, data, user=None):
        request = self.factory.post('/contact/', data=data)
        request.user = user if user is not None else AnonymousUser()
        request.session = {}
        return request

    def _valid_data(self, **overrides):
        data = {
            'topic': 'esp',
            'subject': 'General Inquiry',
            'message': 'Hello, I have a question about upcoming classes.',
            'sender': 'sender@example.com',
            'name': 'Test User',
            'person_type': 'Student',
            'hear_about': 'Friend',
            'anonymous': '',
            'cc_myself': '',
            'decline_password_recovery': '',
            'g-recaptcha-response': 'PASS',
        }
        data.update(overrides)
        return data

    def test_valid_post_sends_email_and_redirects(self):
        """Valid POST sends email to configured topic address and redirects to ?success."""
        data = self._valid_data()
        request = self._post_request(data)
        response = contact(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('?success', response['Location'])
        self.mock_send_mail.assert_called_once()

        args, kwargs = self.mock_send_mail.call_args
        subject, msgtext, from_email, to_email = args[:4]
        self.assertEqual(subject, '[webform] General Inquiry')
        self.assertIn('Hello, I have a question about upcoming classes.', msgtext)
        self.assertEqual(from_email, '"Test User" <sender@example.com>')
        self.assertEqual(to_email, ['esp@example.com'])
        self.assertEqual(kwargs.get('bcc'), [])

    def test_invalid_post_rerenders_form_with_errors(self):
        """POST with missing required fields does not send email and returns 200 with errors."""
        data = {'topic': 'esp', 'sender': 'sender@example.com'}
        request = self._post_request(data)
        response = contact(request)

        self.assertEqual(response.status_code, 200)
        self.mock_send_mail.assert_not_called()
        form = response.context_data['contact_form']
        self.assertFalse(form.is_valid())
        self.assertIn('subject', form.errors)
        self.assertIn('message', form.errors)

    def test_anonymous_post_with_cc_myself_places_sender_in_bcc(self):
        """Anonymous POST with cc_myself puts sender in BCC and topic address in to_email."""
        data = self._valid_data(anonymous='on', cc_myself='on')
        request = self._post_request(data)
        response = contact(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('?success', response['Location'])
        self.mock_send_mail.assert_called_once()

        args, kwargs = self.mock_send_mail.call_args
        from_email, to_email = args[2], args[3]
        bcc = kwargs.get('bcc', [])

        self.assertIn(data['sender'], bcc)
        self.assertNotIn(data['sender'], to_email)
        self.assertEqual(to_email, ['esp@example.com'])
        self.assertEqual(from_email, 'esp@example.com')

    def test_password_keyword_suppresses_send_and_prompts_recovery(self):
        """POST matching user email with password keyword prompts recovery and suppresses sending."""
        ESPUser.objects.create_user(
            username='existing_user',
            password='password123',
            email='sender@example.com',
        )
        data = self._valid_data(
            subject='Help',
            message='I forgot my password, can you help me log in?',
            sender='sender@example.com',
        )
        request = self._post_request(data)
        response = contact(request)

        self.assertEqual(response.status_code, 200)
        self.mock_send_mail.assert_not_called()

        form = response.context_data['contact_form']
        self.assertTrue(form.data.get('decline_password_recovery'))

    def test_declined_password_recovery_sends_email(self):
        """When decline_password_recovery is True, password keywords do not suppress sending."""
        ESPUser.objects.create_user(
            username='existing_user_2',
            password='password123',
            email='sender2@example.com',
        )
        data = self._valid_data(
            subject='Help with password',
            message='I forgot my password, but please send anyway.',
            sender='sender2@example.com',
            decline_password_recovery='on',
        )
        request = self._post_request(data)
        response = contact(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('?success', response['Location'])
        self.mock_send_mail.assert_called_once()
