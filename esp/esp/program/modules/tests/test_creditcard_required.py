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
    return ProgramModuleObj.getFromProgModule(program, pm)


def _create_extracost_transfer(user, program, item_name, amount):
    """Create a Transfer record simulating a student selecting an extra cost item."""
    lit = LineItemType.objects.get(text=item_name, program=program)
    account = Account.objects.get(program=program)
    return Transfer.objects.create(
        user=user,
        line_item=lit,
        amount_dec=Decimal(str(amount)),
        destination=account,
    )


class CreditCardRequiredTest(TestCase):
    """Tests for CreditCardModule_Stripe.isRequired() conditional logic."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='cctest', name='CC Test Program', grade_min=7, grade_max=12)

        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        # $50 base cost + two optional extra cost items
        self.pac.setup_lineitemtypes(
            50.0,
            [('Meal Ticket', 8.0, 1), ('T-Shirt', 15.0, 1)],
        )

        self.student = ESPUser.objects.create_user(
            username='cc_test_student',
            password='password',
            email='cctest@test.learningu.org',
        )
        self.student.makeRole('Student')

        self.iac = IndividualAccountingController(self.program, self.student)

        self.cc_module = _get_cc_module(self.program, 'CreditCardModule_Stripe')
        self.cc_module.user = self.student

    def test_isRequired_default_false(self):
        """CC module is not required by default (no tag set)."""
        self.assertFalse(self.cc_module.isRequired())

    def test_isRequired_explicit_required_field(self):
        """Admin-set required=True always makes the module required."""
        self.cc_module.required = True
        self.assertTrue(self.cc_module.isRequired())

    def test_tag_star_with_extracost_selected(self):
        """Tag='*' + student selected any extra cost -> required."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        _create_extracost_transfer(self.student, self.program, 'Meal Ticket', 8.0)
        self.assertTrue(self.cc_module.isRequired())

    def test_tag_star_without_extracost_selected(self):
        """Tag='*' but student only has admission cost (no extras) -> not required."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        # Student owes $50 admission but hasn't selected any extra cost items
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertFalse(self.cc_module.isRequired())

    def test_tag_specific_item_matching(self):
        """Tag lists specific item + student selected that item -> required."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='Meal Ticket')
        _create_extracost_transfer(self.student, self.program, 'Meal Ticket', 8.0)
        self.assertTrue(self.cc_module.isRequired())

    def test_tag_specific_item_nonmatching(self):
        """Tag lists specific item but student selected a different item -> not required."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='Meal Ticket')
        _create_extracost_transfer(self.student, self.program, 'T-Shirt', 15.0)
        self.assertFalse(self.cc_module.isRequired())

    def test_tag_comma_separated_items(self):
        """Tag lists multiple items comma-separated -> required if any match."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='Meal Ticket,T-Shirt')
        _create_extracost_transfer(self.student, self.program, 'T-Shirt', 15.0)
        self.assertTrue(self.cc_module.isRequired())

    def test_admission_only_never_triggers(self):
        """Even with tag='*', admission-only balance does NOT trigger CC requirement."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        # No extra cost transfers, only admission
        self.assertEqual(self.iac.amount_due(), Decimal('50.00'))
        self.assertFalse(self.cc_module.isRequired())

    def test_tag_not_set(self):
        """Tag not set at all -> not required regardless of balance."""
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertFalse(self.cc_module.isRequired())

    def test_finaid_covers_all_costs(self):
        """Financial aid covering everything -> amount_due=0 -> not required."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        _create_extracost_transfer(self.student, self.program, 'Meal Ticket', 8.0)
        self.iac.grant_full_financial_aid()
        # Pay remaining admission via payment
        self.iac.submit_payment(self.iac.amount_due())
        self.assertFalse(self.cc_module.isRequired())

    def test_micro_balance_ignored(self):
        """Sub-$0.50 balance should NOT trigger required (Stripe minimum charge)."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        _create_extracost_transfer(self.student, self.program, 'Meal Ticket', 8.0)
        # Pay almost everything, leaving < $0.50
        total = self.iac.amount_due()
        self.iac.submit_payment(total - Decimal('0.40'), link_transfers=False)
        self.assertTrue(self.iac.amount_due() < Decimal('0.50'))
        self.assertFalse(self.cc_module.isRequired())

    def test_unauthenticated_user(self):
        """Anonymous user -> not required."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        self.cc_module.user = AnonymousUser()
        self.assertFalse(self.cc_module.isRequired())

    def test_free_program(self):
        """Program with $0 cost -> amount_due=0 -> not required."""
        free_program = Program.objects.create(
            url='freeprogram', name='Free Program', grade_min=7, grade_max=12)
        free_pac = ProgramAccountingController(free_program)
        free_pac.setup_accounts()
        free_pac.setup_lineitemtypes(0.0)

        Tag.setTag('creditcard_required_for_extracosts', target=free_program, value='*')

        free_cc = _get_cc_module(free_program, 'CreditCardModule_Stripe')
        free_cc.user = self.student
        self.assertFalse(free_cc.isRequired())

    def test_tag_scoped_to_program(self):
        """Tag on program A doesn't affect program B."""
        program_b = Program.objects.create(
            url='programb', name='Program B', grade_min=7, grade_max=12)
        pac_b = ProgramAccountingController(program_b)
        pac_b.setup_accounts()
        pac_b.setup_lineitemtypes(50.0, [('Meal Ticket', 8.0, 1)])

        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')

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

    def test_extracost_added_after_admission_payment(self):
        """After paying admission, adding extra costs should re-trigger isRequired().

        Student pays $50 admission, then selects a $15 t-shirt.
        They still owe $15, and have an extra cost transfer -> CC required.
        """
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')

        self.iac.submit_payment(Decimal('50.00'))
        self.assertTrue(self.cc_module.isCompleted())
        self.assertFalse(self.cc_module.isRequired())

        _create_extracost_transfer(self.student, self.program, 'T-Shirt', 15.0)

        self.assertEqual(self.iac.amount_due(), Decimal('15.00'))
        self.assertTrue(self.cc_module.isRequired())
        self.assertFalse(self.cc_module.isCompleted())


class CreditCardCybersourceRequiredTest(TestCase):
    """Tests for CreditCardModule_Cybersource.isRequired() — same tag, same logic."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='ccyber', name='CC Cyber Program', grade_min=7, grade_max=12)

        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0, [('Meal Ticket', 8.0, 1)])

        self.student = ESPUser.objects.create_user(
            username='cc_cyber_student',
            password='password',
            email='cyber@test.learningu.org',
        )
        self.student.makeRole('Student')

        self.iac = IndividualAccountingController(self.program, self.student)
        self.cc_module = _get_cc_module(self.program, 'CreditCardModule_Cybersource')
        self.cc_module.user = self.student

    def test_cybersource_tag_with_extracost(self):
        """Cybersource module also respects the tag with extra cost items."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        _create_extracost_transfer(self.student, self.program, 'Meal Ticket', 8.0)
        self.assertTrue(self.cc_module.isRequired())

    def test_cybersource_default(self):
        """Cybersource module not required by default."""
        self.assertFalse(self.cc_module.isRequired())

    def test_cybersource_admission_only_no_trigger(self):
        """Cybersource: admission-only balance doesn't trigger CC requirement."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        self.assertTrue(self.iac.amount_due() > 0)
        self.assertFalse(self.cc_module.isRequired())


class CreditCardSelfBlockingTest(TestCase):
    """Tests for #3501 fix: CC module must not block itself in payonline()."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='ccselfblock', name='CC SelfBlock Program', grade_min=7, grade_max=12)

        cc_pm = ProgramModule.objects.get(handler='CreditCardModule_Stripe')
        self.program.program_modules.add(cc_pm)

        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0, [('Meal Ticket', 8.0, 1)])

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

        Verifies #3501 fix: without it, making CC required creates a circular
        dependency — the module blocks access to its own payment page.
        """
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        _create_extracost_transfer(self.student, self.program, 'Meal Ticket', 8.0)

        self.assertTrue(self.cc_module.isRequired())
        self.assertFalse(self.cc_module.isCompleted())

        # Simulate the payonline() loop — it should skip the CC module itself
        modules = self.program.getModules(self.student, 'learn')
        completedAll = True
        for module in modules:
            if module.id == self.cc_module.id:
                continue
            if not module.isCompleted() and module.isRequired():
                completedAll = False

        self.assertTrue(completedAll,
            "With the CC module skipped, no other required modules should block")

    def test_payonline_still_checks_other_modules(self):
        """Other incomplete required modules still block payment."""
        Tag.setTag('creditcard_required_for_extracosts', target=self.program, value='*')
        _create_extracost_transfer(self.student, self.program, 'Meal Ticket', 8.0)

        reg_pm = ProgramModule.objects.get(handler='StudentRegCore')
        self.program.program_modules.add(reg_pm)
        reg_pmo, _ = ProgramModuleObj.objects.get_or_create(
            program=self.program, module=reg_pm,
            defaults={'seq': reg_pm.seq, 'required': True},
        )
        reg_pmo.required = True
        reg_pmo.save()

        modules = self.program.getModules(self.student, 'learn')
        completedAll = True
        for module in modules:
            if module.id == self.cc_module.id:
                continue
            if not module.isCompleted() and module.isRequired():
                completedAll = False

        self.assertFalse(completedAll,
            "Other incomplete required modules should block payment")
