"""
Behavioral tests for FinAidApproveModule (esp/program/modules/handlers/finaidapprovemodule.py).

This handler processes POST requests to approve financial aid grants.

Refs: #5044, #3780, #3773
"""

from unittest.mock import patch

from esp.accounting.models import FinancialAidGrant
from esp.program.models import FinancialAidRequest
from esp.program.modules.admin_search import SEARCH_CATEGORY_FINANCIAL
from esp.program.modules.handlers.finaidapprovemodule import FinAidApproveModule
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

    def test_get_with_no_requests_shows_error(self):
        """Admin GET explains when the program has no financial aid requests."""
        self.request.delete()
        self.login_as('admin')

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['error'], 'No requests found.')

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
        self.request.refresh_from_db()
        self.assertTrue(self.request.approved)
        self.assertTrue(self.request.done)

    def test_post_with_approve_blanks_approves_incomplete_request(self):
        """The approve_blanks option allows a request with missing answers."""
        blank_student = self.students[1]
        blank_request = FinancialAidRequest.objects.create(
            program=self.program,
            user=blank_student,
            household_income='',
            extra_explaination='Need details.',
        )
        self.login_as('admin')

        self.client.post(self._url(), {
            'user': [str(blank_student.id)],
            'approve_blanks': 'on',
            'amount_max_dec': '25.00',
            'percent': '100',
        })

        self.assertTrue(
            FinancialAidGrant.objects.filter(request=blank_request).exists(),
            'approve_blanks should allow an incomplete request to be approved'
        )

    def test_post_without_approve_blanks_skips_blank_income(self):
        """POST without approve_blanks skips requests missing required answers."""
        blank_student = self.students[1]
        blank_request = FinancialAidRequest.objects.create(
            program=self.program,
            user=blank_student,
            household_income='',
            extra_explaination='Need details.',
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

    def test_post_without_approve_blanks_skips_blank_explanation(self):
        """A missing explanation also prevents approval when blanks are disallowed."""
        incomplete_student = self.students[1]
        incomplete_request = FinancialAidRequest.objects.create(
            program=self.program,
            user=incomplete_student,
            household_income='30000',
            extra_explaination=None,
        )
        self.login_as('admin')

        self.client.post(self._url(), {
            'user': [str(incomplete_student.id)],
            'amount_max_dec': '25.00',
            'percent': '100',
        })

        self.assertFalse(
            FinancialAidGrant.objects.filter(request=incomplete_request).exists(),
            'Request with a blank explanation should be skipped when approve_blanks is not set'
        )

    def test_post_skips_already_approved_request(self):
        """A request with an existing grant is not approved a second time."""
        FinancialAidGrant.objects.create(request=self.request, percent=100)
        self.login_as('admin')

        with patch.object(FinancialAidRequest, 'approve') as approve:
            response = self.client.post(self._url(), {
                'user': [str(self.student.id)],
                'approve_blanks': 'on',
                'amount_max_dec': '25.00',
                'percent': '100',
            })

        approve.assert_not_called()
        self.assertEqual(response.context['users_approved'], [])
        self.assertEqual(response.context['users_error'], [])
        self.assertEqual(
            FinancialAidGrant.objects.filter(request=self.request).count(), 1
        )

    def test_post_records_approval_value_and_type_errors(self):
        """Conversion errors from request approval are reported to the admin."""
        self.login_as('admin')
        post_data = {
            'user': [str(self.student.id)],
            'approve_blanks': 'on',
            'amount_max_dec': 'not-a-dollar',
            'percent': 'not-a-percent',
        }

        for error in (ValueError, TypeError):
            with self.subTest(error=error.__name__):
                with patch.object(FinancialAidRequest, 'approve', side_effect=error) as approve:
                    response = self.client.post(self._url(), post_data)

                approve.assert_called_once_with(
                    dollar_amount='not-a-dollar',
                    discount_percent='not-a-percent',
                )
                self.assertEqual(response.context['users_approved'], [])
                self.assertEqual(
                    response.context['users_error'], [self.student.name()]
                )
                self.assertFalse(
                    FinancialAidGrant.objects.filter(request=self.request).exists()
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

    def test_is_step_returns_false(self):
        """FinAidApproveModule isStep returns False."""
        self.assertFalse(FinAidApproveModule().isStep())

    def test_module_properties(self):
        """FinAidApproveModule module_properties contains expected keys."""
        props = FinAidApproveModule.module_properties()
        self.assertEqual(props['module_type'], 'manage')
        self.assertEqual(props['admin_title'], 'Easily Approve Financial Aid Requests')

    def test_get_admin_search_entry(self):
        """get_admin_search_entry returns entry for finaidapprove, None for others."""
        entry = FinAidApproveModule.get_admin_search_entry(
            self.program, 'manage', 'finaidapprove', None
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.id, 'manage_finaidapprove')
        self.assertEqual(entry.category, SEARCH_CATEGORY_FINANCIAL)
        self.assertIn('finaidapprove', entry.url)

        # Non-matching view returns None
        entry_none = FinAidApproveModule.get_admin_search_entry(
            self.program, 'manage', 'other_view', None
        )
        self.assertIsNone(entry_none)
