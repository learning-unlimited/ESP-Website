from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from esp.program.modules.handlers import creditcardmodule_stripe as cc_module
from esp.program.modules.handlers.creditcardmodule_stripe import CreditCardModule_Stripe


class CreditCardStripeChargePaymentTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.module = SimpleNamespace(
            program=SimpleNamespace(),
            check_setup=Mock(return_value=True),
            settings={'secret_key': 'sk_test_123'},
            line_item_type=Mock(return_value=SimpleNamespace()),
            send_error_email=Mock(),
            baseDir=Mock(return_value='program/modules/creditcardmodule_stripe/'),
        )
        self.user = SimpleNamespace(id=42, name=Mock(return_value='Test User'))
        self.program = SimpleNamespace(niceName=Mock(return_value='Test Program'))

    def _call(self, post_data):
        request = self.factory.post('/learn/test/charge_payment', post_data)
        request.user = self.user

        fake_iac = SimpleNamespace(
            get_preferences=Mock(return_value=[]),
            set_preference=Mock(),
            get_id=Mock(return_value='PO-1'),
            amount_due=Mock(return_value=0),
            submit_payment=Mock(),
        )
        fake_form = SimpleNamespace(is_valid=Mock(return_value=False), amount=None)

        charge_payment = getattr(
            CreditCardModule_Stripe.charge_payment,
            'method',
            CreditCardModule_Stripe.charge_payment,
        )

        with patch('esp.program.modules.handlers.creditcardmodule_stripe.IndividualAccountingController', return_value=fake_iac), \
             patch('esp.program.modules.handlers.creditcardmodule_stripe.DonationModule.get_form', return_value=fake_form), \
             patch('esp.program.modules.handlers.creditcardmodule_stripe.Tag.getTag', return_value=None), \
             patch('esp.program.modules.handlers.creditcardmodule_stripe.render_to_response', return_value='failure-response'), \
             patch.object(cc_module.settings, 'INSTITUTION_NAME', 'Institute', create=True), \
             patch.object(cc_module.settings, 'ORGANIZATION_SHORT_NAME', 'Org', create=True):
            return charge_payment(self.module, request, None, None, None, None, None, self.program)

    def test_missing_stripe_token_returns_failure(self):
        response = self._call({'ponumber': 'PO-1', 'totalcost_cents': '5000'})

        self.assertEqual(response, 'failure-response')
        self.module.send_error_email.assert_called_once()

    def test_missing_totalcost_cents_returns_failure(self):
        response = self._call({'ponumber': 'PO-1', 'stripeToken': 'tok_test_123'})

        self.assertEqual(response, 'failure-response')
        self.module.send_error_email.assert_called_once()