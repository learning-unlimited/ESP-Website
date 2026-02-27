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
"""
Tests for esp.accounting.controllers
Source: esp/esp/accounting/controllers.py

Tests GlobalAccountingController, ProgramAccountingController, and
IndividualAccountingController.
"""
from decimal import Decimal

from django.contrib.auth.models import Group

from esp.accounting.controllers import (
    GlobalAccountingController,
    IndividualAccountingController,
    ProgramAccountingController,
)
from esp.accounting.models import (
    Account,
    LineItemType,
    Transfer,
)
from esp.program.models import Program
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class GlobalAccountingControllerTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()

    def test_setup_accounts(self):
        gac = GlobalAccountingController()
        accounts = gac.setup_accounts()
        self.assertEqual(len(accounts), 3)
        names = [a.name for a in accounts]
        self.assertIn('receivable', names)
        self.assertIn('payable', names)
        self.assertIn('grants', names)

    def test_setup_accounts_idempotent(self):
        gac = GlobalAccountingController()
        gac.setup_accounts()
        gac.setup_accounts()
        self.assertEqual(Account.objects.filter(name='receivable').count(), 1)


class ProgramAccountingControllerTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)

    def test_setup_accounts(self):
        account = self.pac.setup_accounts()
        self.assertIsNotNone(account)
        self.assertEqual(account.program, self.program)

    def test_setup_lineitemtypes(self):
        self.pac.setup_accounts()
        result = self.pac.setup_lineitemtypes(50.0)
        texts = [lit.text for lit in result]
        self.assertIn('Program admission', texts)
        self.assertIn('Student payment', texts)
        self.assertIn('Financial aid grant', texts)

    def test_setup_lineitemtypes_with_optional(self):
        self.pac.setup_accounts()
        result = self.pac.setup_lineitemtypes(
            50.0,
            optional_items=[('T-shirt', 15.0, 1)],
        )
        texts = [lit.text for lit in result]
        self.assertIn('T-shirt', texts)

    def test_default_program_account(self):
        self.pac.setup_accounts()
        account = self.pac.default_program_account()
        self.assertIsNotNone(account)

    def test_default_program_account_none(self):
        account = self.pac.default_program_account()
        self.assertIsNone(account)

    def test_default_payments_lineitemtype(self):
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)
        lit = self.pac.default_payments_lineitemtype()
        self.assertIsNotNone(lit)
        self.assertTrue(lit.for_payments)

    def test_classify_transfer_payment(self):
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)
        payment_lit = self.pac.default_payments_lineitemtype()
        account = self.pac.default_program_account()
        transfer = Transfer.objects.create(
            destination=account,
            line_item=payment_lit,
            amount_dec=Decimal('50.00'),
        )
        self.assertEqual(self.pac.classify_transfer(transfer), 'Payment')

    def test_classify_transfer_finaid(self):
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)
        finaid_lit = self.pac.default_finaid_lineitemtype()
        account = self.pac.default_program_account()
        transfer = Transfer.objects.create(
            destination=account,
            line_item=finaid_lit,
            amount_dec=Decimal('50.00'),
        )
        self.assertEqual(self.pac.classify_transfer(transfer), 'Financial aid')

    def test_payments_summary_empty(self):
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)
        count, total = self.pac.payments_summary()
        self.assertEqual(count, 0)


class IndividualAccountingControllerTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.user = ESPUser.objects.create_user(
            username='teststu', password='password',
        )
        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)
        self.iac = IndividualAccountingController(self.program, self.user)

    def test_get_id(self):
        expected = '%d/%d' % (self.program.id, self.user.id)
        self.assertEqual(self.iac.get_id(), expected)

    def test_from_id(self):
        id_str = self.iac.get_id()
        restored = IndividualAccountingController.from_id(id_str)
        self.assertEqual(restored.program, self.program)
        self.assertEqual(restored.user, self.user)

    def test_transfers_to_program_exist_false(self):
        self.assertFalse(self.iac.transfers_to_program_exist())

    def test_ensure_required_transfers(self):
        self.iac.ensure_required_transfers()
        transfers = Transfer.objects.filter(user=self.user)
        self.assertTrue(transfers.exists())

    def test_amount_requested(self):
        amount = self.iac.amount_requested()
        self.assertEqual(amount, Decimal('50.00'))

    def test_amount_paid_zero(self):
        self.assertEqual(self.iac.amount_paid(), Decimal('0'))

    def test_has_paid_false(self):
        self.assertFalse(self.iac.has_paid())

    def test_amount_due(self):
        due = self.iac.amount_due()
        self.assertEqual(due, Decimal('50.00'))

    def test_str(self):
        result = str(self.iac)
        self.assertIn('Accounting for', result)

    def test_set_finaid_params(self):
        self.iac.set_finaid_params(25.0, 50)
        grant = self.iac.latest_finaid_grant()
        self.assertIsNotNone(grant)
        self.assertEqual(grant.percent, 50)
        self.assertEqual(grant.amount_max_dec, Decimal('25.00'))

    def test_grant_full_financial_aid(self):
        self.iac.grant_full_financial_aid()
        grant = self.iac.latest_finaid_grant()
        self.assertIsNotNone(grant)
        self.assertEqual(grant.percent, 100)

    def test_revoke_financial_aid(self):
        self.iac.grant_full_financial_aid()
        self.iac.revoke_financial_aid()
        self.assertIsNone(self.iac.latest_finaid_grant())

    def test_amount_finaid_with_full_grant(self):
        self.iac.grant_full_financial_aid()
        finaid = self.iac.amount_finaid()
        self.assertEqual(finaid, Decimal('50.00'))

    def test_amount_due_with_full_finaid(self):
        self.iac.grant_full_financial_aid()
        self.assertEqual(self.iac.amount_due(), Decimal('0.00'))

    def test_amount_due_with_partial_finaid(self):
        self.iac.set_finaid_params(20.0, 0)
        due = self.iac.amount_due()
        self.assertEqual(due, Decimal('30.00'))
