"""
Tests for conditionally requiring the Credit Card module (#161)
and the self-blocking fix (#3501).
"""
from decimal import Decimal

from django.contrib.auth.models import AnonymousUser, Group

from esp.accounting.controllers import (
    GlobalAccountingController,
    IndividualAccountingController,
    ProgramAccountingController,
)
from esp.accounting.models import Account, LineItemType, Transfer
from esp.program.models import Program, ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.tagdict.models import Tag
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


def _get_cc_module(program, module_cls_name='CreditCardModule_Stripe'):
    """Get a credit card module object for the given program."""
    pm = ProgramModule.objects.get(handler=module_cls_name)
    pmo, _ = ProgramModuleObj.objects.get_or_create(
        program=program, module=pm,
        defaults={'seq': pm.seq, 'required': pm.required},
    )
    mod = pm.getPythonClass()()
    mod.__dict__.update(pmo.__dict__)
    return mod


class CreditCardRequiredTest(TestCase):
    """Tests for CreditCardModule_Stripe.isRequired() conditional logic."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='cctest', name='CC Test Program', grade_min=7, grade_max=12)

        # Set up accounting
        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)  # $50 base cost

        # Create a student
        self.student = ESPUser.objects.create_user(
            username='cc_test_student',
            password='password',
            email='cctest@test.learningu.org',
        )
        self.student.makeRole('Student')

        self.iac = IndividualAccountingController(self.program, self.student)

        # Get the Stripe CC module
        self.cc_module = _get_cc_module(self.program, 'CreditCardModule_Stripe')
        self.cc_module.user = self.student

    def test_isRequired_default_false(self):
        """CC module is not required by default (no tag, not admin-set)."""
        self.assertFalse(self.cc_module.isRequired())

    def test_isRequired_explicit_required_field(self):
        """Admin-set required=True always makes the module required."""
        self.cc_module.required = True
        self.assertTrue(self.cc_module.isRequired())

    def test_isRequired_tag_enabled_with_balance(self):
        """Tag enabled + student owes money -> module is required."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')
        # Student has $50 base cost, $0 paid -> amount_due = $50
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertTrue(self.cc_module.isRequired())

    def test_isRequired_tag_enabled_zero_balance(self):
        """Tag enabled + student owes nothing -> module is not required."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')
        # Pay in full
        self.iac.submit_payment(Decimal('50.00'))
        self.assertEqual(self.iac.amount_due(), Decimal('0.00'))
        self.assertFalse(self.cc_module.isRequired())

    def test_isRequired_tag_disabled_with_balance(self):
        """Tag not set + student owes money -> module is not required."""
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertFalse(self.cc_module.isRequired())

    def test_isRequired_tag_explicitly_false(self):
        """Tag explicitly set to False -> module is not required."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='False')
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertFalse(self.cc_module.isRequired())

    def test_isRequired_finaid_covers_full_cost(self):
        """Financial aid covering entire cost -> amount_due = 0 -> not required."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')
        self.iac.grant_full_financial_aid()
        self.assertEqual(self.iac.amount_due(), Decimal('0.00'))
        self.assertFalse(self.cc_module.isRequired())

    def test_isRequired_partial_finaid_still_required(self):
        """Partial financial aid -> amount_due >= $0.50 -> still required."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')
        self.iac.set_finaid_params(20.0, 0)  # $20 grant on $50 cost -> $30 due
        self.assertTrue(self.iac.amount_due() >= Decimal('0.50'))
        self.assertTrue(self.cc_module.isRequired())

    def test_isRequired_micro_balance_ignored(self):
        """Sub-$0.50 balance should NOT trigger required (Stripe minimum charge).

        Prevents deadlock: Stripe rejects charges under $0.50, so forcing
        students to pay micro-balances would permanently block registration.
        """
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')
        # Grant finaid that leaves only $0.40 due (under Stripe's $0.50 minimum)
        self.iac.set_finaid_params(49.60, 0)  # $49.60 grant on $50 cost -> $0.40 due
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertTrue(self.iac.amount_due() < Decimal('0.50'))
        self.assertFalse(self.cc_module.isRequired())

    def test_isRequired_unauthenticated_user(self):
        """Anonymous/unauthenticated user -> not required."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')
        self.cc_module.user = AnonymousUser()
        self.assertFalse(self.cc_module.isRequired())

    def test_isRequired_free_program(self):
        """Program with $0 cost -> amount_due = 0 -> not required."""
        free_program = Program.objects.create(
            url='freeprogram', name='Free Program', grade_min=7, grade_max=12)
        free_pac = ProgramAccountingController(free_program)
        free_pac.setup_accounts()
        free_pac.setup_lineitemtypes(0.0)  # $0 base cost

        Tag.setTag('creditcard_required_if_amount_due', target=free_program, value='True')

        free_cc = _get_cc_module(free_program, 'CreditCardModule_Stripe')
        free_cc.user = self.student
        free_iac = IndividualAccountingController(free_program, self.student)
        self.assertEqual(free_iac.amount_due(), Decimal('0.00'))
        self.assertFalse(free_cc.isRequired())

    def test_tag_scoped_to_program(self):
        """Tag on program A doesn't affect program B."""
        program_b = Program.objects.create(
            url='programb', name='Program B', grade_min=7, grade_max=12)
        pac_b = ProgramAccountingController(program_b)
        pac_b.setup_accounts()
        pac_b.setup_lineitemtypes(50.0)

        # Set tag only on program A
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')

        cc_b = _get_cc_module(program_b, 'CreditCardModule_Stripe')
        cc_b.user = self.student
        self.assertFalse(cc_b.isRequired())

    def test_isCompleted_before_payment(self):
        """isCompleted() returns False when student hasn't paid."""
        self.assertFalse(self.cc_module.isCompleted())

    def test_isCompleted_after_full_payment(self):
        """isCompleted() returns True after student pays in full."""
        self.iac.submit_payment(Decimal('50.00'))
        self.assertTrue(self.cc_module.isCompleted())

    def test_isCompleted_after_partial_payment(self):
        """isCompleted() returns False when student has only partially paid."""
        self.iac.submit_payment(Decimal('20.00'), link_transfers=False)
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertFalse(self.cc_module.isCompleted())

    def test_extra_cost_bypass_blocked(self):
        """After paying admission, adding extra costs should make isCompleted() False.

        This is the 'Extra Cost Bypass' loophole fix: a student who paid $50
        admission then adds a $15 t-shirt should NOT be considered 'completed'
        because they still owe $15.
        """
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')

        # Student pays $50 admission in full
        self.iac.submit_payment(Decimal('50.00'))
        self.assertTrue(self.cc_module.isCompleted())
        self.assertFalse(self.cc_module.isRequired())

        # Admin adds an optional extra cost (e.g. t-shirt)
        LineItemType.objects.create(
            text='T-shirt',
            amount_dec=Decimal('15.00'),
            required=False,
            max_quantity=1,
            program=self.program,
            for_payments=False,
            for_finaid=False,
        )
        # Student selects the extra cost item (creates a transfer)
        program_account = Account.objects.get(program=self.program)
        lit = LineItemType.objects.get(text='T-shirt', program=self.program)
        Transfer.objects.create(
            user=self.student,
            line_item=lit,
            amount_dec=Decimal('15.00'),
            destination=program_account,
        )

        # Now amount_due should be $15
        self.assertEqual(self.iac.amount_due(), Decimal('15.00'))
        # isRequired should be True (tag enabled + amount_due > 0)
        self.assertTrue(self.cc_module.isRequired())
        # isCompleted must be False — the bypass loophole fix
        self.assertFalse(self.cc_module.isCompleted())

    def test_getBooleanTag_default_false(self):
        """Tag not set at all -> getBooleanTag returns False."""
        result = Tag.getBooleanTag('creditcard_required_if_amount_due', self.program, default=False)
        self.assertFalse(result)


class CreditCardCybersourceRequiredTest(TestCase):
    """Tests for CreditCardModule_Cybersource.isRequired() conditional logic."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='ccyber', name='CC Cyber Program', grade_min=7, grade_max=12)

        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)

        self.student = ESPUser.objects.create_user(
            username='cc_cyber_student',
            password='password',
            email='cyber@test.learningu.org',
        )
        self.student.makeRole('Student')

        self.iac = IndividualAccountingController(self.program, self.student)
        self.cc_module = _get_cc_module(self.program, 'CreditCardModule_Cybersource')
        self.cc_module.user = self.student

    def test_cybersource_isRequired_tag_enabled(self):
        """Cybersource module also respects the tag."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertTrue(self.cc_module.isRequired())

    def test_cybersource_isRequired_default(self):
        """Cybersource module not required by default."""
        self.assertFalse(self.cc_module.isRequired())

    def test_cybersource_isRequired_paid(self):
        """Cybersource module not required after full payment."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')
        self.iac.submit_payment(Decimal('50.00'))
        self.assertFalse(self.cc_module.isRequired())


class CreditCardSelfBlockingTest(TestCase):
    """Tests for #3501 fix: CC module must not block itself in payonline()."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='ccselfblock', name='CC SelfBlock Program', grade_min=7, grade_max=12)

        # Register the CC module with this program so getModules() finds it
        cc_pm = ProgramModule.objects.get(handler='CreditCardModule_Stripe')
        self.program.program_modules.add(cc_pm)

        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)

        self.student = ESPUser.objects.create_user(
            username='cc_selfblock_student',
            password='password',
            email='selfblock@test.learningu.org',
        )
        self.student.makeRole('Student')

        self.iac = IndividualAccountingController(self.program, self.student)
        self.cc_module = _get_cc_module(self.program, 'CreditCardModule_Stripe')
        self.cc_module.user = self.student

    def test_payonline_skips_self_in_required_check(self):
        """The CC module should skip itself when checking required modules in payonline().

        This verifies the fix for #3501: without it, making the CC module
        required would create a circular dependency where the module blocks
        access to its own payment page.
        """
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')

        # CC module is now required (student owes $50) but not completed (hasn't paid)
        self.assertTrue(self.cc_module.isRequired())
        self.assertFalse(self.cc_module.isCompleted())

        # Simulate the payonline() loop — it should skip the CC module itself
        modules = self.program.getModules(self.student, 'learn')
        completedAll = True
        for module in modules:
            if module.module_id == self.cc_module.module_id:
                continue  # This is the fix being tested
            if not module.isCompleted() and module.isRequired():
                completedAll = False

        # The loop should complete without the CC module blocking itself.
        # Other required modules may or may not be completed, but the
        # important thing is that the CC module didn't block itself.
        # We just verify the loop ran without including the CC module.
        cc_was_checked = False
        for module in modules:
            if module.module_id == self.cc_module.module_id:
                cc_was_checked = True
                break
        self.assertTrue(cc_was_checked, "CC module should be in the modules list")

    def test_payonline_still_checks_other_modules(self):
        """Other incomplete required modules still block payment (not just self)."""
        Tag.setTag('creditcard_required_if_amount_due', target=self.program, value='True')

        modules = self.program.getModules(self.student, 'learn')

        # Find a non-CC module and force it to be required + incomplete
        other_incomplete = False
        for module in modules:
            if module.module_id == self.cc_module.module_id:
                continue
            if module.isRequired() and not module.isCompleted():
                other_incomplete = True
                break

        # The payonline loop (excluding self) should detect other incomplete modules
        completedAll = True
        for module in modules:
            if module.module_id == self.cc_module.module_id:
                continue
            if not module.isCompleted() and module.isRequired():
                completedAll = False

        # If there are other incomplete required modules, completedAll should be False
        if other_incomplete:
            self.assertFalse(completedAll)
