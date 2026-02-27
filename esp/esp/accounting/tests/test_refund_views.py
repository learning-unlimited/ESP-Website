"""
Tests for the Stripe refund admin pages.
"""

from decimal import Decimal
from unittest.mock import patch

from django.core import mail

import stripe

from esp.accounting.models import Transfer
from esp.program.tests import ProgramFrameworkTest


class RefundViewsTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        # Setup basic program framework with users
        kwargs.update({
            'num_students': 1,
            'num_admins': 1,
        })
        super().setUp(*args, **kwargs)

        self.admin = self.admins[0]
        self.student = self.students[0]

        # Setup accounting and create a mock payment transfer for the student
        from esp.accounting.controllers import ProgramAccountingController
        pac = ProgramAccountingController(self.program)
        pac.clear_all_data()
        pac.setup_accounts()
        pac.setup_lineitemtypes(25.00)

        self.payment_type = pac.default_payments_lineitemtype()

        # Create a standalone mock Stripe transaction
        self.transfer = Transfer.objects.create(
            user=self.student,
            amount=Decimal('25.00'),
            line_item=self.payment_type,
            transaction_id='ch_mock_charge_123',
            source=None,  # Null source indicates external payment (Stripe)
        )

    def test_refund_search_access(self):
        """Only admins should be able to access the refund page."""
        # Non-admin
        self.client.login(username=self.student.username, password='password')
        response = self.client.get('/accounting/refund/')
        self.assertTemplateUsed(response, '403.html')

        # Admin
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/accounting/refund/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounting/refund.html')

    @patch('stripe.Charge.retrieve')
    def test_refund_search_results(self, mock_retrieve):
        """Searching by program should return Stripe transactions."""
        class MockCharge:
            amount_refunded = 500  # $5.00 refunded previously
            amount = 2500          # $25.00 total
        mock_retrieve.return_value = MockCharge()

        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/accounting/refund/', {'program': self.program.id, 'user': self.student.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'refund_amount_{self.transfer.id}')
        self.assertContains(response, self.student.username)
        # Check that amount remaining is correctly calculated: 25 - 5 = $20.00
        self.assertContains(response, '20.00')

    @patch('stripe.Refund.create')
    def test_process_refund_success(self, mock_refund_create):
        """Valid refund requests should call Stripe and send a success email."""
        class MockRefund:
            id = 're_mock_refund_456'
        mock_refund_create.return_value = MockRefund()

        self.client.login(username=self.admin.username, password='password')
        mail.outbox = []

        response = self.client.post('/accounting/refund/process/', {
            'program_id': self.program.id,
            f'refund_amount_{self.transfer.id}': '10.00',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounting/refund_confirmation.html')
        # There's a newline in the template between 'processed' and 'successfully',
        # so check for something else that indicates success.
        self.assertContains(response, 'cfo@learningu.org')
        self.assertContains(response, self.student.username)

        # Verify Stripe API was called with correct charge ID and amount in cents (10.00 -> 1000)
        mock_refund_create.assert_called_once_with(
            charge='ch_mock_charge_123',
            amount=1000
        )

        # Verify success email was sent to CFO
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Stripe refunds issued', mail.outbox[0].subject)
        self.assertIn('cfo@learningu.org', mail.outbox[0].to)
        self.assertIn('10.00', mail.outbox[0].body)
        self.assertIn(self.student.username, mail.outbox[0].body)

    @patch('stripe.Refund.create')
    def test_process_refund_error(self, mock_refund_create):
        """Stripe errors should be caught, displayed to user, and trigger an error email."""
        mock_refund_create.side_effect = stripe.error.StripeError("Insufficient funds on Stripe account")

        self.client.login(username=self.admin.username, password='password')
        mail.outbox = []

        response = self.client.post('/accounting/refund/process/', {
            'program_id': self.program.id,
            f'refund_amount_{self.transfer.id}': '25.00',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounting/refund_confirmation.html')
        self.assertContains(response, 'Failed')
        self.assertContains(response, 'Insufficient funds on Stripe account')

        # Verify error email was sent to CFO
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Stripe refund error', mail.outbox[0].subject)
        self.assertIn('cfo@learningu.org', mail.outbox[0].to)
        self.assertIn('Insufficient funds on Stripe account', mail.outbox[0].body)

    def test_process_refund_no_amounts(self):
        """Submitting process without any refund amounts should show an error."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.post('/accounting/refund/process/', {
            'program_id': self.program.id,
            # No refund amounts provided
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounting/refund_error.html')
        self.assertContains(response, 'No valid refund amounts were specified')

    @patch('stripe.Charge.retrieve')
    def test_refund_search_post(self, mock_retrieve):
        """Searching via POST should return Stripe transactions."""
        class MockCharge:
            amount_refunded = 500
            amount = 2500
        mock_retrieve.return_value = MockCharge()

        self.client.login(username=self.admin.username, password='password')
        response = self.client.post('/accounting/refund/', {
            'search': '1',
            'program': self.program.id,
            'target_user': self.student.id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'refund_amount_{self.transfer.id}')
        self.assertContains(response, self.student.username)

    def test_process_refund_get(self):
        """GET request to process_refund should return the search form."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/accounting/refund/process/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounting/refund.html')

    def test_process_refund_invalid_program(self):
        """POST to process_refund with invalid program should return an error."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.post('/accounting/refund/process/', {
            'program_id': 99999,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounting/refund_error.html')
        self.assertContains(response, 'Invalid program specified.')

    def test_process_refund_invalid_amount(self):
        """POST to process_refund with an invalid amount or transfer should just ignore it and error on empty."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.post('/accounting/refund/process/', {
            'program_id': self.program.id,
            f'refund_amount_{self.transfer.id}': 'invalid_amount',
            'refund_amount_99999': '10.00',  # Invalid transfer ID
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounting/refund_error.html')
        self.assertContains(response, 'No valid refund amounts were specified.')

    def test_refund_invalid_program_and_user_get(self):
        """GET request to refund with invalid program and user shouldn't crash."""
        self.client.login(username=self.admin.username, password='password')
        response = self.client.get('/accounting/refund/', {'program': 99999, 'user': 99999})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounting/refund.html')
