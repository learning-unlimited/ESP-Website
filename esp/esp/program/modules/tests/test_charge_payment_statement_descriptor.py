"""
Regression test: Stripe's statement_descriptor field forbids '*', ',', and
'"' (https://docs.stripe.com/changelog/2019-02-19/changes-statement-
descriptor-behaviors-charges) and rejects the charge outright if present.
group_name (from the full_group_name Tag, or institution settings as a
fallback) is not guaranteed to avoid those characters before being truncated
to Stripe's 22-character limit, so charge_payment must strip them first.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import RequestFactory

from esp.accounting.controllers import (
    GlobalAccountingController,
    IndividualAccountingController,
    ProgramAccountingController,
)
from esp.program.models import Program, ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.handlers.creditcardmodule_stripe import CreditCardModule_Stripe
from esp.tagdict.models import Tag
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _get_cc_module(program):
    pm = ProgramModule.objects.get(handler='CreditCardModule_Stripe')
    return ProgramModuleObj.getFromProgModule(program, pm)


class ChargePaymentStatementDescriptorTests(TestCase):
    def setUp(self):
        super().setUp()
        self.program = Program.objects.create(
            url='ccdescriptor', name='CC Descriptor Test Program', grade_min=7, grade_max=12,
        )

        gac = GlobalAccountingController()
        gac.setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)

        self.student = ESPUser.objects.create_user(
            username='cc_descriptor_student',
            password='password',
            email='ccdescriptor@test.learningu.org',
        )
        self.student.makeRole('Student')

        self.iac = IndividualAccountingController(self.program, self.student)
        self.cc_module = _get_cc_module(self.program)
        self.cc_module.user = self.student
        self.cc_module.program = self.program

        settings.STRIPE_CONFIG = {
            'secret_key': 'sk_test_' + 'A' * 24,
            'publishable_key': 'pk_test_' + 'A' * 24,
        }

        self.factory = RequestFactory()

    def _call_charge_payment(self, group_name):
        Tag.setTag('full_group_name', value=group_name)

        request = self.factory.post('/charge_payment', {
            'totalcost_cents': str(int(self.iac.amount_due() * 100)),
            'stripeToken': 'tok_visa',
            'ponumber': self.iac.get_id(),
        })
        request.user = self.student

        fake_charge = MagicMock()
        fake_charge.id = 'ch_test_123'

        with patch(
            'esp.program.modules.handlers.creditcardmodule_stripe.stripe.Charge.create',
            return_value=fake_charge,
        ) as mock_create:
            fn = getattr(
                CreditCardModule_Stripe.charge_payment, 'method', CreditCardModule_Stripe.charge_payment,
            )
            fn(self.cc_module, request, 'learn', None, None, None, None, self.program)

        return mock_create

    def test_forbidden_characters_are_stripped(self):
        """A group name containing *, comma, and a double quote must not
        reach Stripe with those characters still present."""
        mock_create = self._call_charge_payment('Some*Group, "Name"')
        mock_create.assert_called_once()
        descriptor = mock_create.call_args.kwargs['statement_descriptor']
        self.assertNotIn('*', descriptor)
        self.assertNotIn(',', descriptor)
        self.assertNotIn('"', descriptor)

    def test_descriptor_still_respects_the_22_character_limit(self):
        """Stripping forbidden characters must not bypass Stripe's 22-char cap."""
        mock_create = self._call_charge_payment('A Very Long Institution Name, Inc."')
        descriptor = mock_create.call_args.kwargs['statement_descriptor']
        self.assertLessEqual(len(descriptor), 22)

    def test_clean_group_name_is_unaffected(self):
        """A group name with no forbidden characters passes through untouched
        (up to the 22-character truncation already in place)."""
        mock_create = self._call_charge_payment('Learning Unlimited')
        descriptor = mock_create.call_args.kwargs['statement_descriptor']
        self.assertEqual(descriptor, 'Learning Unlimited'[0:22])

    def test_description_field_is_not_sanitized(self):
        """Only statement_descriptor has Stripe's character restriction --
        the human-readable description field must still contain the group
        name's original punctuation."""
        mock_create = self._call_charge_payment('Some*Group, "Name"')
        description = mock_create.call_args.kwargs['description']
        self.assertIn('Some*Group, "Name"', description)
