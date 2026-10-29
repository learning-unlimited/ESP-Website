from django.test import TestCase, RequestFactory
from esp.accounting.views import user_summary
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser


class AccountingModuleTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = ESPUser.objects.create_user(
            username="test_admin",
            password="password123"
        )
        self.user.makeAdmin()

    def test_user_lookup_via_url_target_user(self):
        request = self.factory.get(
            f"/accounting/?target_user={self.user.id}"
        )
        request.user = self.user

        response = user_summary(request)

        self.assertEqual(response.status_code, 200)

    def test_user_lookup_via_post_data(self):
        """
        Verify lookup via POST data
        """
        request = self.factory.post(
            "/accounting/",
            {"target_user": self.user.id}
        )
        request.user = self.user

        response = user_summary(request)

        self.assertEqual(response.status_code, 200)

    def test_invalid_user_lookup(self):
        """
        Invalid user should not crash the view
        """
        request = self.factory.get("/accounting/?target_user=99999")
        request.user = self.user

        response = user_summary(request)

        self.assertEqual(response.status_code, 200)


class AccountingModuleHandlerTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
    """
    Regression tests for AccountingModule.accounting handler (issue #6124).
    Verifies that invalid, non-existent, or malformed user IDs in the URL
    do not cause unhandled HTTP 500 errors and gracefully fall back to the
    user search interface.
    """

    def setUp(self):
        super().setUp()
        self.admin = self.login_as('admin')
        self.student = self.students[0]
        self.base_url = self.get_module_url('manage', 'accounting')

    def test_nonexistent_user_id(self):
        """
        Test A: A non-existent numeric user ID should be handled gracefully,
        returning HTTP 200 and falling back to the user search interface.
        """
        response = self.client.get(f"{self.base_url}/999999")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/accountingmodule/accounting.html')
        self.assertIsNone(response.context['target_user'])
        self.assertNotIn('prog_results', response.context)
        self.assertIn('form', response.context)

    def test_non_numeric_user_id(self):
        """
        Test B: A non-numeric user ID (e.g. 'abc') should not cause an unhandled
        ORM ValueError or HTTP 500, falling back to the user search interface.
        """
        response = self.client.get(f"{self.base_url}/abc")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/accountingmodule/accounting.html')
        self.assertIsNone(response.context['target_user'])
        self.assertNotIn('prog_results', response.context)
        self.assertIn('form', response.context)

    def test_missing_or_empty_extra(self):
        """
        Test C: Missing or empty extra retains expected behavior (search interface).
        """
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/accountingmodule/accounting.html')
        self.assertIsNone(response.context['target_user'])
        self.assertIn('form', response.context)

    def test_valid_existing_user_id(self):
        """
        Test D: A valid existing user ID properly loads that user's accounting data.
        """
        response = self.client.get(f"{self.base_url}/{self.student.id}")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/accountingmodule/accounting.html')
        self.assertEqual(response.context['target_user'], self.student)
        self.assertIn('prog_results', response.context)

    def test_boundary_user_ids(self):
        """
        Boundary values like 0 or negative integers should be handled gracefully
        without producing an unhandled HTTP 500.
        """
        for boundary_id in ["0", "-1"]:
            response = self.client.get(f"{self.base_url}/{boundary_id}")
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'program/modules/accountingmodule/accounting.html')
            self.assertIsNone(response.context['target_user'])
            self.assertNotIn('prog_results', response.context)
            self.assertIn('form', response.context)

    def test_post_valid_target_user(self):
        """
        A valid target_user POST selects the intended user and returns
        the expected accounting results.
        """
        response = self.client.post(self.base_url, {'target_user': self.student.id})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/accountingmodule/accounting.html')
        self.assertEqual(response.context['target_user'], self.student)
        self.assertIn('prog_results', response.context)

    def test_post_invalid_target_user(self):
        """
        An invalid POST retains form-validation behavior without crashing.
        """
        response = self.client.post(self.base_url, {'target_user': ''})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/accountingmodule/accounting.html')
        self.assertIsNone(response.context['target_user'])
        self.assertNotIn('prog_results', response.context)
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())

    def test_unauthorized_access_denied(self):
        """
        Verify that an unauthorized user cannot gain access through either
        a valid or malformed user ID.
        """
        self.login_as('student')
        # Student with valid ID gets 'not an admin' error page
        response_valid = self.client.get(f"{self.base_url}/{self.student.id}")
        self.assertEqual(response_valid.status_code, 200)
        self.assertTemplateUsed(response_valid, 'errors/program/notanadmin.html')

        # Student with malformed ID gets 'not an admin' error page
        response_malformed = self.client.get(f"{self.base_url}/abc")
        self.assertEqual(response_malformed.status_code, 200)
        self.assertTemplateUsed(response_malformed, 'errors/program/notanadmin.html')

        # Anonymous user gets redirected to login
        self.logout()
        response_anon = self.client.get(f"{self.base_url}/{self.student.id}")
        self.assertEqual(response_anon.status_code, 302)
