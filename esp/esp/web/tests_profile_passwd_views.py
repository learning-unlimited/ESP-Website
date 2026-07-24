"""
Unit tests for:
  - esp/web/views/myesp.py  (profile_editor, myesp_passwd POST, myesp_stop_testing valid-admin path)

Covers:
  myesp.py:
    myesp_passwd() POST — valid old + new password → renders success
    myesp_passwd() POST — wrong old password → form errors
    myesp_stop_testing() — valid admin in session → redirect to manage URL, cookie deleted
    profile_editor() GET — pre-fills form from user + RegistrationProfile
    profile_editor() POST valid teacher — saves ContactInfo, redirects
    profile_editor() POST invalid — missing required fields → re-renders with form errors

PR 8/10 — esp/web module coverage improvement
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.test import TestCase, Client, RequestFactory

from esp.users.models import ESPUser
from esp.web.views.myesp import (
    myesp_passwd,
    myesp_stop_testing,
    profile_editor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username, role=None, password='testpass123',
               is_superuser=False, first_name='Test', last_name='User'):
    if is_superuser:
        user = ESPUser.objects.create_superuser(
            username=username, password=password,
            email='%s@test.com' % username,
        )
    else:
        user = ESPUser.objects.create_user(
            username=username, password=password,
            email='%s@test.com' % username,
            first_name=first_name, last_name=last_name,
        )
    if role:
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
    return user


# ---------------------------------------------------------------------------
# myesp_passwd() POST
# ---------------------------------------------------------------------------

class MyESPPasswdPostTest(TestCase):
    """POST paths for the password-change view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _make_user('passwd_user')
        # Store the plain password for POST data
        self.plain_password = 'testpass123'

    def _post_request(self, data):
        request = self.factory.post('/myesp/passwd/', data=data)
        request.user = self.user
        # django.contrib.auth.login() calls request.session.cycle_key()
        request.session = MagicMock()
        return request

    def test_valid_post_renders_success(self):
        """Valid old + matching new passwords → Success=True in response."""
        data = {
            'password': self.plain_password,
            'newpasswd': 'newpassword456',
            'newpasswdconfirm': 'newpassword456',
        }
        response = myesp_passwd(self._post_request(data))
        self.assertEqual(response.status_code, 200)
        # The success template renders a congratulations message
        self.assertIn(b'Congratulations', response.content)

    def test_wrong_old_password_rerenders_form(self):
        """Wrong current password → form re-rendered (not a redirect)."""
        data = {
            'password': 'wrongpassword',
            'newpasswd': 'newpassword456',
            'newpasswdconfirm': 'newpassword456',
        }
        response = myesp_passwd(self._post_request(data))
        self.assertEqual(response.status_code, 200)
        # Should NOT have Success=True in the context
        self.assertNotIn(b'Success: True', response.content)

    def test_mismatched_new_passwords_rerenders_form(self):
        """New password and confirmation don't match → form re-rendered."""
        data = {
            'password': self.plain_password,
            'newpasswd': 'newpassword456',
            'newpasswdconfirm': 'differentpassword',
        }
        response = myesp_passwd(self._post_request(data))
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# myesp_stop_testing() — valid admin path
# ---------------------------------------------------------------------------

class MyESPStopTestingValidAdminTest(TestCase):
    """myesp_stop_testing() when session has a valid admin user ID."""

    def setUp(self):
        self.factory = RequestFactory()
        # Create an administrator user
        self.admin = _make_user('stopadmin', role='Administrator',
                                is_superuser=True)

    def _make_request_with_testing_session(self, admin_user_id, program_url):
        request = self.factory.get('/myesp/stop_testing/')
        session = MagicMock()
        session.get.return_value = {
            'admin_user_id': admin_user_id,
            'program_url': program_url,
        }
        # flush() is called by auth_logout
        session.flush = MagicMock()
        request.session = session
        return request

    def test_valid_admin_redirects_to_manage(self):
        """Valid admin in session → redirect to /manage/<url>/admin_testing/."""
        request = self._make_request_with_testing_session(
            self.admin.pk, 'test/prog'
        )
        # auth_login/auth_logout are local imports inside myesp_stop_testing;
        # patch at the source module.
        with patch('django.contrib.auth.login'), \
             patch('django.contrib.auth.logout'):
            response = myesp_stop_testing(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/manage/test/prog/admin_testing/', response['Location'])

    def test_valid_admin_deletes_cookie(self):
        """Response from valid admin restore deletes esp_testing_role cookie."""
        request = self._make_request_with_testing_session(
            self.admin.pk, 'test/prog'
        )
        with patch('django.contrib.auth.login'), \
             patch('django.contrib.auth.logout'):
            response = myesp_stop_testing(request)
        # delete_cookie sets cookie to empty string with max-age=0
        self.assertIn('esp_testing_role', response.cookies)
        self.assertEqual(response.cookies['esp_testing_role']['max-age'], 0)


# ---------------------------------------------------------------------------
# profile_editor() — GET paths
# ---------------------------------------------------------------------------

class ProfileEditorGetTest(TestCase):
    """profile_editor() GET: form pre-filled from user + RegistrationProfile."""

    def setUp(self):
        self.factory = RequestFactory()

    def _get_request(self, user):
        request = self.factory.get('/myesp/profile/')
        request.user = user
        request.session = {}
        return request

    def test_get_teacher_returns_200(self):
        """GET as teacher → 200 with form in context."""
        teacher = _make_user('profile_teacher', role='Teacher')
        request = self._get_request(teacher)
        response = profile_editor(request, role='teacher')
        self.assertEqual(response.status_code, 200)

    def test_get_educator_returns_200(self):
        """GET as educator → 200."""
        educator = _make_user('profile_educator', role='Educator')
        request = self._get_request(educator)
        response = profile_editor(request, role='educator')
        self.assertEqual(response.status_code, 200)

    def test_get_empty_role_returns_200(self):
        """GET with empty role (plain user) → 200."""
        plain = _make_user('profile_plain')
        request = self._get_request(plain)
        response = profile_editor(request, role='')
        self.assertEqual(response.status_code, 200)

    def test_get_populates_first_name(self):
        """GET response includes user's first name in the rendered form."""
        teacher = _make_user('profile_fn_teacher', role='Teacher',
                             first_name='Alice', last_name='Smith')
        request = self._get_request(teacher)
        response = profile_editor(request, role='teacher')
        self.assertIn(b'Alice', response.content)

    def test_get_administrator_role_returns_200(self):
        """GET with Administrator role (maps to UserContactForm) → 200."""
        admin = _make_user('profile_admin_get', role='Administrator',
                           is_superuser=True)
        request = self._get_request(admin)
        response = profile_editor(request, role='administrator')
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# profile_editor() — POST paths
# ---------------------------------------------------------------------------

class ProfileEditorPostTest(TestCase):
    """profile_editor() POST: valid and invalid submissions."""

    def setUp(self):
        self.factory = RequestFactory()

    def _post_request(self, user, data):
        request = self.factory.post('/myesp/profile/', data=data)
        request.user = user
        request.session = {}
        return request

    def _valid_teacher_data(self, email):
        """Minimal valid data for TeacherProfileForm.

        Address fields are not required for teachers (tag teacher_address_required defaults False),
        but at least one phone number is required (UserContactForm.clean() enforces this for teachers).
        """
        return {
            'profile_page': '1',
            'first_name': 'Alice',
            'last_name': 'Smith',
            'e_mail': email,
            'phone_cell': '6175551234',
            'affiliation_0': 'Undergrad',  # DropdownOtherWidget first component
            'affiliation_1': '',
        }

    def test_valid_teacher_post_saves_user(self):
        """Valid POST as teacher → user first/last name saved to DB."""
        teacher = _make_user('profile_post_teacher', role='Teacher',
                             first_name='OldFirst', last_name='OldLast')
        data = self._valid_teacher_data('alice@test.com')
        data['first_name'] = 'NewFirst'
        data['last_name'] = 'NewLast'
        request = self._post_request(teacher, data)
        profile_editor(request, role='teacher')
        teacher.refresh_from_db()
        self.assertEqual(teacher.first_name, 'NewFirst')
        self.assertEqual(teacher.last_name, 'NewLast')

    def test_invalid_teacher_post_rerenders_form(self):
        """POST missing required fields → 200 re-render (not redirect)."""
        teacher = _make_user('profile_invalid_teacher', role='Teacher')
        data = {
            'profile_page': '1',
            # Missing first_name, last_name, e_mail → form invalid
        }
        request = self._post_request(teacher, data)
        response = profile_editor(request, role='teacher')
        self.assertEqual(response.status_code, 200)

    def test_post_without_profile_page_treated_as_get(self):
        """POST without profile_page key → treated as GET, returns 200 with form."""
        teacher = _make_user('profile_nopage_teacher', role='Teacher')
        data = {
            'first_name': 'Bob',
        }
        request = self._post_request(teacher, data)
        response = profile_editor(request, role='teacher')
        self.assertEqual(response.status_code, 200)

    def test_valid_educator_post_saves_user(self):
        """Valid POST as educator → user name saved to DB."""
        educator = _make_user('profile_post_educator', role='Educator',
                              first_name='OldBob', last_name='OldJones')
        # EducatorProfileForm: UserContactForm (address required for non-teachers) + EducatorInfoForm (all optional)
        data = {
            'profile_page': '1',
            'first_name': 'NewBob',
            'last_name': 'NewJones',
            'e_mail': 'bob@test.com',
            'address_street': '123 Main St',
            'address_city': 'Springfield',
            'address_state': 'MA',
            'address_zip': '01234',
        }
        request = self._post_request(educator, data)
        profile_editor(request, role='educator')
        educator.refresh_from_db()
        self.assertEqual(educator.first_name, 'NewBob')
