"""
Unit tests for:
  - esp/web/views/main.py
  - esp/web/views/myesp.py

Covers:
  main.py:
    set_csrf_token(), home(), archives() dispatch,
    public_email(), contact() (tag-disabled redirect, GET, success param),
    FAQView, ContactUsView, registration_redirect()

  myesp.py:
    myesp_accountmanage(), myesp_passwd() (GET, onsite error),
    myesp_stop_testing() (no-session, non-admin session),
    edit_profile() role routing

PR 6/6 — esp/web module coverage improvement
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser, Group
from django.test import RequestFactory
from esp.tests.util import CacheFlushTestCase as TestCase

from esp.middleware import ESPError_NoLog
from esp.users.models import ESPUser
from esp.web.views.main import (
    set_csrf_token,
    home,
    archives,
    public_email,
    contact,
    FAQView,
    ContactUsView,
    registration_redirect,
)
from esp.web.views.myesp import (
    myesp_accountmanage,
    myesp_passwd,
    myesp_stop_testing,
    edit_profile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username, role=None, password='testpass', is_superuser=False):
    if is_superuser:
        user = ESPUser.objects.create_superuser(
            username=username, password=password,
            email='%s@test.com' % username,
        )
    else:
        user = ESPUser.objects.create_user(
            username=username, password=password,
            email='%s@test.com' % username,
            first_name='Test', last_name='User',
        )
    if role:
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
    return user


def _request_with_session(factory, path, user, session_data=None):
    """Build a RequestFactory request with a session dict attached."""
    request = factory.get(path)
    request.user = user
    request.session = session_data if session_data is not None else {}
    return request


# ---------------------------------------------------------------------------
# set_csrf_token()
# ---------------------------------------------------------------------------

class SetCsrfTokenTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_200(self):
        request = self.factory.get('/set_csrf_token')
        request.user = AnonymousUser()
        response = set_csrf_token(request)
        self.assertEqual(response.status_code, 200)

    def test_returns_empty_body(self):
        request = self.factory.get('/set_csrf_token')
        request.user = AnonymousUser()
        response = set_csrf_token(request)
        self.assertEqual(response.content, b'')


# ---------------------------------------------------------------------------
# home()
# ---------------------------------------------------------------------------

class HomeViewTest(TestCase):

    def test_home_returns_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_contains_html(self):
        response = self.client.get('/')
        self.assertIn(b'<html', response.content.lower())


# ---------------------------------------------------------------------------
# archives() dispatch
# Note: archive_teachers() and archive_programs() accept 3 args but
# archives() passes 4 (source bug). Those two are tested directly in their
# own dedicated tests; here we test 'classes' and the unknown fallback.
# ---------------------------------------------------------------------------

class ArchivesDispatchTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_classes_selection_dispatched(self):
        request = self.factory.get('/archives/classes/')
        request.user = AnonymousUser()
        response = archives(request, 'classes')
        self.assertEqual(response.status_code, 200)

    def test_unknown_selection_returns_construction_page(self):
        request = self.factory.get('/archives/unknown/')
        request.user = AnonymousUser()
        response = archives(request, 'unknown')
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# public_email()
# Note: public_email raises ESPError, whose concrete instances
# (ESPError_Log/ESPError_NoLog) inherit from Exception; these tests simply
# assert that an Exception is propagated for invalid/nonexistent IDs.
# ---------------------------------------------------------------------------

class PublicEmailTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_invalid_id_raises_exception(self):
        request = self.factory.get('/email/99999/')
        request.user = AnonymousUser()
        with self.assertRaises(ESPError_NoLog):
            public_email(request, 99999)

    def test_nonexistent_id_raises_exception(self):
        # A second non-existent ID to confirm behaviour is consistent
        request = self.factory.get('/email/88888/')
        request.user = AnonymousUser()
        with self.assertRaises(ESPError_NoLog):
            public_email(request, 88888)


# ---------------------------------------------------------------------------
# contact() — tag paths
# ---------------------------------------------------------------------------

class ContactViewTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        # Ensure tag is absent so default = False (redirect)
        from esp.tagdict.models import Tag
        Tag.objects.filter(key='contact_form_enabled').delete()

    def test_tag_disabled_redirects(self):
        request = self.factory.get('/contact/')
        request.user = AnonymousUser()
        # Mock getBooleanTag to return False (tag disabled)
        with patch('esp.web.views.main.Tag.getBooleanTag', return_value=False):
            response = contact(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/contact.html')

    def test_get_with_tag_enabled_returns_200(self):
        from esp.tagdict.models import Tag
        Tag.objects.get_or_create(
            key='contact_form_enabled',
            defaults={'value': 'True'},
        )
        request = self.factory.get('/contact/')
        request.user = AnonymousUser()
        response = contact(request)
        self.assertEqual(response.status_code, 200)

    def test_success_param_returns_200(self):
        from esp.tagdict.models import Tag
        Tag.objects.get_or_create(
            key='contact_form_enabled',
            defaults={'value': 'True'},
        )
        request = self.factory.get('/contact/', {'success': ''})
        request.user = AnonymousUser()
        response = contact(request, section='esp')
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# FAQView / ContactUsView
# ---------------------------------------------------------------------------

class FAQViewTest(TestCase):

    def test_faq_view_returns_200(self):
        request = RequestFactory().get('/faq/')
        request.user = AnonymousUser()
        response = FAQView.as_view()(request)
        self.assertEqual(response.status_code, 200)


class ContactUsViewTest(TestCase):

    def test_contact_us_view_returns_200(self):
        request = RequestFactory().get('/contact_us/')
        request.user = AnonymousUser()
        response = ContactUsView.as_view()(request)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# registration_redirect()
# ---------------------------------------------------------------------------

class RegistrationRedirectTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, user):
        return _request_with_session(self.factory, '/register/', user)

    def test_no_role_user_returns_200(self):
        user = _make_user('norole_user')
        response = registration_redirect(self._request(user))
        self.assertEqual(response.status_code, 200)

    def test_student_no_programs_returns_200(self):
        user = _make_user('reg_student', role='Student')
        response = registration_redirect(self._request(user))
        self.assertEqual(response.status_code, 200)

    def test_teacher_no_programs_returns_200(self):
        user = _make_user('reg_teacher', role='Teacher')
        response = registration_redirect(self._request(user))
        self.assertEqual(response.status_code, 200)

    def test_volunteer_no_programs_returns_200(self):
        user = _make_user('reg_volunteer', role='Volunteer')
        response = registration_redirect(self._request(user))
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# myesp_accountmanage()
# ---------------------------------------------------------------------------

class MyESPAccountManageTest(TestCase):

    def test_direct_view_returns_200(self):
        user = _make_user('acct_user')
        request = _request_with_session(RequestFactory(), '/myesp/accountmanage/', user)
        response = myesp_accountmanage(request)
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# myesp_passwd()
# ---------------------------------------------------------------------------

class MyESPPasswdTest(TestCase):

    def test_get_renders_form(self):
        user = _make_user('passwd_user')
        request = _request_with_session(RequestFactory(), '/myesp/passwd/', user)
        response = myesp_passwd(request)
        self.assertEqual(response.status_code, 200)

    def test_onsite_username_raises_exception(self):
        # 'onsite' user is created by install(); fetch it instead of creating
        user = ESPUser.objects.get(username='onsite')
        request = _request_with_session(RequestFactory(), '/myesp/passwd/', user)
        with self.assertRaises(Exception):
            myesp_passwd(request)


# ---------------------------------------------------------------------------
# myesp_stop_testing()
# ---------------------------------------------------------------------------

class MyESPStopTestingTest(TestCase):

    def test_no_testing_session_redirects_home(self):
        user = _make_user('stop_test_user')
        request = _request_with_session(RequestFactory(), '/myesp/stop_testing/', user)
        response = myesp_stop_testing(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_non_admin_in_session_redirects_home(self):
        regular_user = _make_user('nonadmin_test')
        # Use MagicMock so we can control request.session.get(...)'s return value
        mock_session = MagicMock()
        mock_session.get.return_value = {
            'admin_user_id': regular_user.id,
            'program_url': 'TestProg/2024_Fall',
        }
        request = RequestFactory().get('/myesp/stop_testing/')
        request.user = regular_user
        request.session = mock_session
        response = myesp_stop_testing(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_nonexistent_user_in_session_redirects_home(self):
        user = _make_user('nonexist_test')
        mock_session = MagicMock()
        mock_session.get.return_value = {
            'admin_user_id': 999999,
            'program_url': 'TestProg/2024_Fall',
        }
        request = RequestFactory().get('/myesp/stop_testing/')
        request.user = user
        request.session = mock_session
        response = myesp_stop_testing(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')


# ---------------------------------------------------------------------------
# edit_profile() — role routing
# ---------------------------------------------------------------------------

class EditProfileTest(TestCase):

    def _get(self, user):
        # profile_editor calls updateOnsite(request) which needs request.session
        return _request_with_session(RequestFactory(), '/myesp/profile/', user)

    def test_teacher_routed(self):
        user = _make_user('ep_teacher', role='Teacher')
        response = edit_profile(self._get(user))
        self.assertIn(response.status_code, [200, 302])

    def test_student_routed(self):
        user = _make_user('ep_student', role='Student')
        response = edit_profile(self._get(user))
        self.assertIn(response.status_code, [200, 302])

    def test_guardian_routed(self):
        user = _make_user('ep_guardian', role='Guardian')
        response = edit_profile(self._get(user))
        self.assertIn(response.status_code, [200, 302])

    def test_educator_routed(self):
        user = _make_user('ep_educator', role='Educator')
        response = edit_profile(self._get(user))
        self.assertIn(response.status_code, [200, 302])

    def test_volunteer_routed(self):
        user = _make_user('ep_volunteer', role='Volunteer')
        response = edit_profile(self._get(user))
        self.assertIn(response.status_code, [200, 302])
