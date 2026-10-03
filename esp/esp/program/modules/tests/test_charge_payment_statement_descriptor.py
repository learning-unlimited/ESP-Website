"""
Regression tests for Stripe statement_descriptor sanitization (Issue #5914).

Stripe rejects the charge if statement_descriptor contains any of
<, >, backslash, ', " or * (https://docs.stripe.com/get-started/account/statement-descriptors).
Commas are stripped too, to be safe. group_name (from the
full_group_name Tag, or institution settings as a fallback) is not guaranteed
to avoid those characters before being truncated to Stripe's 22-character limit,
so charge_payment must strip them first.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import RequestFactory, override_settings

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


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


def _get_cc_module(program):
    pm = ProgramModule.objects.get(handler='CreditCardModule_Stripe')
    return ProgramModuleObj.getFromProgModule(program, pm)


@override_settings(
    STRIPE_CONFIG={
        'secret_key': 'sk_test_' + 'A' * 24,
        'publishable_key': 'pk_test_' + 'A' * 24,
    }
)
class ChargePaymentStatementDescriptorTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()

        self.program = Program.objects.create(
            url='ccdescriptor',
            name='CC Descriptor Test Program',
            grade_min=7,
            grade_max=12,
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

        self.factory = RequestFactory()

    def tearDown(self):
        Tag.unSetTag('full_group_name')
        super().tearDown()

    def _call_charge_payment(self, group_name=None):
        if group_name is not None:
            Tag.setTag('full_group_name', value=group_name)
        else:
            Tag.unSetTag('full_group_name')

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
            response = fn(self.cc_module, request, 'learn', None, None, None, None, self.program)

        self.last_response = response
        mock_create.response = response
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
        self.assertEqual(descriptor, 'SomeGroup Name')

    def test_apostrophe_angle_brackets_and_backslash_are_stripped(self):
        """Stripe also rejects apostrophes, angle brackets and backslashes."""
        mock_create = self._call_charge_payment("St. Mary's <ESP>\\")
        mock_create.assert_called_once()
        descriptor = mock_create.call_args.kwargs['statement_descriptor']
        self.assertEqual(descriptor, 'St. Marys ESP')

    def test_descriptor_still_respects_the_22_character_limit(self):
        """Stripping forbidden characters must occur before truncating to 22 chars."""
        # Stripping *, ", and , from this 28-char string yields:
        # '12345678901234567890Extra'
        # Truncating to 22 characters then yields:
        # '12345678901234567890Ex'
        mock_create = self._call_charge_payment('1234567890*,"1234567890Extra')
        mock_create.assert_called_once()
        descriptor = mock_create.call_args.kwargs['statement_descriptor']
        self.assertLessEqual(len(descriptor), 22)
        self.assertEqual(descriptor, '12345678901234567890Ex')

    def test_clean_group_name_is_unaffected(self):
        """A group name with no forbidden characters passes through untouched."""
        mock_create = self._call_charge_payment('Learning Unlimited')
        mock_create.assert_called_once()
        descriptor = mock_create.call_args.kwargs['statement_descriptor']
        self.assertEqual(descriptor, 'Learning Unlimited')

    def test_description_field_is_not_sanitized(self):
        """Only statement_descriptor has Stripe's character restriction --
        the human-readable description field must still contain the group
        name's original punctuation."""
        mock_create = self._call_charge_payment('Some*Group, "Name"')
        mock_create.assert_called_once()
        description = mock_create.call_args.kwargs['description']
        self.assertIn('Some*Group, "Name"', description)
        self.assertEqual(
            description,
            f"Payment for Some*Group, \"Name\" {self.program.niceName()} - {self.student.name()}"
        )

    @override_settings(INSTITUTION_NAME='MIT, Inc.', ORGANIZATION_SHORT_NAME='ESP*')
    def test_fallback_institution_settings_descriptor_is_sanitized(self):
        """When full_group_name tag is not set, group_name falls back to
        f'{settings.INSTITUTION_NAME} {settings.ORGANIZATION_SHORT_NAME}'.
        Forbidden characters in that fallback must also be stripped."""
        mock_create = self._call_charge_payment(group_name=None)
        mock_create.assert_called_once()
        descriptor = mock_create.call_args.kwargs['statement_descriptor']
        self.assertNotIn('*', descriptor)
        self.assertNotIn(',', descriptor)
        self.assertNotIn('"', descriptor)
        self.assertEqual(descriptor, 'MIT Inc. ESP')
        description = mock_create.call_args.kwargs['description']
        self.assertIn('MIT, Inc. ESP*', description)

    def test_sanitized_statement_descriptor_is_reused_in_success_context(self):
        """The sanitized statement descriptor sent to Stripe must also be
        used in the success page context, while description retains the original name."""
        mock_create = self._call_charge_payment('Learning Unlimited, Inc.')
        mock_create.assert_called_once()
        descriptor = mock_create.call_args.kwargs['statement_descriptor']
        self.assertEqual(descriptor, 'Learning Unlimited Inc')
        self.assertEqual(self.last_response.context_data['statement_descriptor'], descriptor)
        description = mock_create.call_args.kwargs['description']
        self.assertIn('Learning Unlimited, Inc.', description)
