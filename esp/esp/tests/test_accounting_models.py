"""
Tests for esp.accounting.models
Source: esp/esp/accounting/models.py

Tests LineItemType, LineItemOptions, Account, Transfer, and FinancialAidGrant models.
"""
from decimal import Decimal

from django.contrib.auth.models import Group

from esp.accounting.models import (
    Account,
    FinancialAidGrant,
    LineItemOptions,
    LineItemType,
    Transfer,
)
from esp.program.models import FinancialAidRequest, Program
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class LineItemTypeTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.lit = LineItemType.objects.create(
            text='Test Item',
            amount_dec=Decimal('25.00'),
            program=self.program,
            required=True,
            max_quantity=1,
        )

    def test_amount_property(self):
        self.assertEqual(self.lit.amount, 25.0)

    def test_amount_property_none(self):
        self.lit.amount_dec = None
        self.assertIsNone(self.lit.amount)

    def test_num_options_zero(self):
        self.assertEqual(self.lit.num_options, 0)

    def test_num_options_with_options(self):
        LineItemOptions.objects.create(
            lineitem_type=self.lit,
            description='Option A',
            amount_dec=Decimal('10.00'),
        )
        self.assertEqual(self.lit.num_options, 1)

    def test_options_cost_range_none_when_empty(self):
        self.assertIsNone(self.lit.options_cost_range)

    def test_options_cost_range_with_options(self):
        LineItemOptions.objects.create(
            lineitem_type=self.lit,
            description='Cheap',
            amount_dec=Decimal('5.00'),
        )
        LineItemOptions.objects.create(
            lineitem_type=self.lit,
            description='Expensive',
            amount_dec=Decimal('50.00'),
        )
        cost_range = self.lit.options_cost_range
        self.assertIsNotNone(cost_range)

    def test_has_custom_options_false(self):
        self.assertFalse(self.lit.has_custom_options)

    def test_has_custom_options_true(self):
        LineItemOptions.objects.create(
            lineitem_type=self.lit,
            description='Custom',
            amount_dec=Decimal('0.00'),
            is_custom=True,
        )
        self.assertTrue(self.lit.has_custom_options)

    def test_str_with_amount(self):
        result = str(self.lit)
        self.assertIn('Test Item', result)
        self.assertIn('25.00', result)

    def test_str_without_amount(self):
        self.lit.amount_dec = Decimal('0')
        self.lit.save()
        result = str(self.lit)
        self.assertIn('Test Item', result)


class LineItemOptionsTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.lit = LineItemType.objects.create(
            text='Test Item',
            amount_dec=Decimal('25.00'),
            program=self.program,
        )
        self.option_with_amount = LineItemOptions.objects.create(
            lineitem_type=self.lit,
            description='With Amount',
            amount_dec=Decimal('15.00'),
        )
        self.option_without_amount = LineItemOptions.objects.create(
            lineitem_type=self.lit,
            description='Inherits',
            amount_dec=None,
        )

    def test_amount_dec_inherited_with_own_amount(self):
        self.assertEqual(self.option_with_amount.amount_dec_inherited, Decimal('15.00'))

    def test_amount_dec_inherited_from_parent(self):
        self.assertEqual(self.option_without_amount.amount_dec_inherited, Decimal('25.00'))

    def test_amount_property(self):
        self.assertEqual(self.option_with_amount.amount, 15.0)

    def test_amount_property_none(self):
        self.assertIsNone(self.option_without_amount.amount)

    def test_str(self):
        result = str(self.option_with_amount)
        self.assertIn('With Amount', result)
        self.assertIn('15.00', result)


class AccountTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.account = Account.objects.create(
            name='test-account',
            description='Test Title\nTest body content',
            program=self.program,
        )
        self.lit = LineItemType.objects.create(
            text='Item',
            amount_dec=Decimal('10.00'),
            program=self.program,
        )

    def test_balance_empty(self):
        self.assertEqual(self.account.balance, 0)

    def test_balance_with_incoming_transfer(self):
        Transfer.objects.create(
            destination=self.account,
            line_item=self.lit,
            amount_dec=Decimal('50.00'),
        )
        self.assertEqual(self.account.balance, Decimal('50.00'))

    def test_balance_with_outgoing_transfer(self):
        Transfer.objects.create(
            source=self.account,
            line_item=self.lit,
            amount_dec=Decimal('30.00'),
        )
        self.assertEqual(self.account.balance, Decimal('-30.00'))

    def test_description_title(self):
        self.assertEqual(self.account.description_title, 'Test Title')

    def test_description_contents(self):
        self.assertEqual(self.account.description_contents, 'Test body content')

    def test_str(self):
        self.assertEqual(str(self.account), 'test-account')


class TransferTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.account_src = Account.objects.create(
            name='source', description='Source', program=self.program,
        )
        self.account_dst = Account.objects.create(
            name='destination', description='Dest', program=self.program,
        )
        self.lit = LineItemType.objects.create(
            text='Item',
            amount_dec=Decimal('10.00'),
            program=self.program,
        )
        self.transfer = Transfer.objects.create(
            source=self.account_src,
            destination=self.account_dst,
            line_item=self.lit,
            amount_dec=Decimal('42.50'),
        )

    def test_get_amount(self):
        self.assertEqual(self.transfer.get_amount(), 42.5)

    def test_set_amount(self):
        self.transfer.set_amount(99.99)
        self.assertEqual(self.transfer.amount_dec, Decimal('99.99'))

    def test_set_amount_raises_when_paid(self):
        payment = Transfer.objects.create(
            source=self.account_src,
            destination=self.account_dst,
            line_item=self.lit,
            amount_dec=Decimal('42.50'),
        )
        self.transfer.paid_in = payment
        self.transfer.save()
        with self.assertRaises(Exception):
            self.transfer.set_amount(10.0)

    def test_str(self):
        result = str(self.transfer)
        self.assertIn('42.50', result)
        self.assertIn('source', result)
        self.assertIn('destination', result)
