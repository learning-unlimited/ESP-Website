from django.test import TestCase

from esp.accounting.cybersource import compute_signature, verify_signature


class CybersourceSignatureTest(TestCase):
    """Unit tests for the Secure Acceptance HMAC signing helpers, independent
    of any view or live Cybersource account."""

    def setUp(self):
        self.secret = 'test-secret-key'
        self.fields = {
            'access_key': 'ak123',
            'profile_id': 'pid456',
            'transaction_uuid': 'uuid789',
            'merchant_id': 'esp_test',
            'amount': '25.00',
        }
        self.signed_field_names = 'access_key,profile_id,transaction_uuid,merchant_id,amount'

    def _signed_post_data(self):
        data = dict(self.fields)
        data['signed_field_names'] = self.signed_field_names
        data['unsigned_field_names'] = ''
        data['signature'] = compute_signature(self.fields, self.signed_field_names, self.secret)
        return data

    def test_compute_signature_is_deterministic(self):
        sig1 = compute_signature(self.fields, self.signed_field_names, self.secret)
        sig2 = compute_signature(self.fields, self.signed_field_names, self.secret)
        self.assertEqual(sig1, sig2)

    def test_compute_signature_changes_with_field_value(self):
        sig1 = compute_signature(self.fields, self.signed_field_names, self.secret)
        tampered = dict(self.fields, amount='999.00')
        sig2 = compute_signature(tampered, self.signed_field_names, self.secret)
        self.assertNotEqual(sig1, sig2)

    def test_verify_signature_accepts_correctly_signed_data(self):
        self.assertTrue(verify_signature(self._signed_post_data(), self.secret))

    def test_verify_signature_rejects_tampered_amount(self):
        data = self._signed_post_data()
        data['amount'] = '999.00'  # changed after signing
        self.assertFalse(verify_signature(data, self.secret))

    def test_verify_signature_rejects_wrong_secret(self):
        data = self._signed_post_data()
        self.assertFalse(verify_signature(data, 'wrong-secret'))

    def test_verify_signature_rejects_missing_signature(self):
        data = self._signed_post_data()
        del data['signature']
        self.assertFalse(verify_signature(data, self.secret))

    def test_verify_signature_rejects_missing_signed_field_names(self):
        data = self._signed_post_data()
        del data['signed_field_names']
        self.assertFalse(verify_signature(data, self.secret))

    def test_verify_signature_rejects_missing_signed_field(self):
        data = self._signed_post_data()
        del data['amount']  # listed in signed_field_names but absent
        self.assertFalse(verify_signature(data, self.secret))

    def test_verify_signature_rejects_empty_post(self):
        self.assertFalse(verify_signature({}, self.secret))
