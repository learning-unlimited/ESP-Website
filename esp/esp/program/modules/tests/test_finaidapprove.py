"""
Behavioral tests for FinAidApproveModule (esp/program/modules/handlers/finaidapprovemodule.py).

This handler processes POST requests to approve financial aid grants.

Refs: #3780, #3773
"""

from esp.accounting.models import FinancialAidGrant
from esp.program.models import FinancialAidRequest
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest


class FinAidApproveTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self):
        super().setUp()
        # Create a financial aid request for the first student
        self.student = self.students[0]
        self.request = FinancialAidRequest.objects.create(
            program=self.program,
            user=self.student,
            household_income='30000',
            extra_explaination='Need help.',
        )

    def _url(self):
        return self.get_module_url('manage', 'finaidapprove')

    def test_get_returns_200_with_requests_in_context(self):
        """Admin GET returns 200 and the requests queryset is in context."""
        self.login_as('admin')
        response = self.assert_view_ok(self._url())
        self.assertIn('requests', response.context)

    def test_student_get_is_forbidden(self):
        """Non-admin GET renders the notanadmin error page (ESP returns 200 for auth errors)."""
        self.login_as('student')
        response = self.client.get(self._url())
        # ESP's @needs_admin renders a 200 error page rather than 302/403.
        self.assertEqual(response.status_code, 200)
        # The error template is errors/program/notanadmin.html
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

    def test_post_creates_financial_aid_grant(self):
        """POST with a valid user ID and amount creates a FinancialAidGrant."""
        self.login_as('admin')
        response = self.client.post(self._url(), {
            'user': [str(self.student.id)],
            'approve_blanks': 'on',
            'amount_max_dec': '25.00',
            'percent': '100',
        })
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(
            FinancialAidGrant.objects.filter(request=self.request).exists(),
            'A FinancialAidGrant should be created after POST approval'
        )

    def test_post_without_approve_blanks_skips_blank_income(self):
        """POST without approve_blanks does not approve requests with blank income."""
        # Create a request with blank household_income
        blank_student = self.students[1]
        blank_request = FinancialAidRequest.objects.create(
            program=self.program,
            user=blank_student,
            household_income='',
            extra_explaination='',
        )
        self.login_as('admin')
        self.client.post(self._url(), {
            'user': [str(blank_student.id)],
            # approve_blanks NOT set
            'amount_max_dec': '25.00',
            'percent': '100',
        })
        self.assertFalse(
            FinancialAidGrant.objects.filter(request=blank_request).exists(),
            'Request with blank income should be skipped when approve_blanks is not set'
        )

    def test_post_without_user_in_checklist_does_not_approve(self):
        """POST that omits a user ID from the checklist does not approve that user."""
        self.login_as('admin')
        self.client.post(self._url(), {
            'user': [],  # no user selected
            'approve_blanks': 'on',
            'amount_max_dec': '25.00',
            'percent': '100',
        })
        self.assertFalse(
            FinancialAidGrant.objects.filter(request=self.request).exists(),
            'Request should not be approved when user is not in the checklist'
        )
