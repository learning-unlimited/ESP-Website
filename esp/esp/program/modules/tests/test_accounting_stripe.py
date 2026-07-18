from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json
from io import BytesIO
from urllib.error import HTTPError
import datetime

from esp.program.models import Program
from esp.tagdict.models import Tag
from esp.program.modules.handlers.accountingmodule import AccountingModule
from esp.accounting.models import Transfer, LineItemType, Account
from esp.users.models import ESPUser

class StripeTotalsTest(TestCase):
    def setUp(self):
        self.program = Program.objects.create(
            name="Test Program",
            url="testprog",
            grade_min=7,
            grade_max=12
        )
        self.module = AccountingModule()

        # Configure CC tag (using 'stripe_settings' key as required by logic)
        stripe_config = {
            'secret_key': 'sk_test_123',
            'donation_text': 'Donation to Learning Unlimited'
        }
        from django.conf import settings
        settings.STRIPE_CONFIG = stripe_config

        # Create a "Student payment" transfer to establish a start time
        self.lit_payment = LineItemType.objects.create(text="Student payment", program=self.program)
        self.account = Account.objects.create(program=self.program, name="Test Account")
        self.user = ESPUser.objects.create(username="donor")

        # We need to explicitly set timestamp because auto_now will set it to now
        with patch('django.utils.timezone.now', return_value=datetime.datetime(2023, 1, 15, tzinfo=datetime.timezone.utc)):
             self.transfer = Transfer.objects.create(
                amount_dec=Decimal('50.00'),
                line_item=self.lit_payment,
                destination=self.account,
                user=self.user,
                transaction_id="ch_1"
            )

    @patch('urllib.request.urlopen')
    def test_get_cc_totals_success(self, mock_urlopen):
        # Mock Search API response (now using Charges List API)
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'data': [
                {
                    'id': 'ch_1',
                    'amount': 5000,
                    'amount_refunded': 1000,
                    'created': 1673740800, # 2023-01-15
                    'description': 'Student payment for Test Program',
                    'balance_transaction': {
                        'fee': 150
                    }
                }
            ],
            'has_more': False
        }).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        totals = self.module._get_cc_totals(self.program)

        self.assertEqual(totals['gross_amount'], Decimal('50.00'))
        self.assertEqual(totals['gross_count'], 1)
        self.assertEqual(totals['refunded_amount'], Decimal('10.00'))
        self.assertEqual(totals['total_stripe_fees'], Decimal('1.50'))
        self.assertTrue(totals['is_configured'])

    def test_get_cc_totals_not_configured(self):
        # Remove tag
        from django.conf import settings
        settings.STRIPE_CONFIG = {}

        totals = self.module._get_cc_totals(self.program)
        self.assertIsNone(totals)

    def test_fee_calculation(self):
        # Test the new fee formula: (Donation Count * 0.01) + (Donation Amount * 0.022)
        lit_donation = LineItemType.objects.create(text="Donation to Learning Unlimited", program=self.program)

        Transfer.objects.create(
            amount_dec=Decimal('100.00'),
            line_item=lit_donation,
            destination=self.account,
            user=self.user
        )

        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps({'data': [], 'has_more': False}).encode('utf-8')
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            totals = self.module._get_cc_totals(self.program)

            # (1 * 0.01) + (100 * 0.022) = 0.01 + 2.2 = 2.21
            self.assertEqual(totals['cc_donation_fees'], Decimal('2.21'))
            self.assertEqual(totals['donation_amount'], Decimal('100.00'))
            self.assertEqual(totals['donation_count'], 1)
