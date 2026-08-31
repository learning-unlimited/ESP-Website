"""Tests for esp.utils.safe_pickle.

These pin the property the module exists for: a blob that this application
did not write is never handed to pickle.
"""
import pickle

from django.test import TestCase, override_settings

from esp.utils import safe_pickle


class SafePickleTest(TestCase):

    def test_round_trip(self):
        for value in ({'a': 1}, [1, 2, 3], 'text', None, {1, 2}):
            self.assertEqual(safe_pickle.loads(safe_pickle.dumps(value)), value)

    def test_dumps_with_payload_matches_plain_pickle(self):
        """The unsigned payload must stay comparable with pre-signing rows."""
        blob, payload = safe_pickle.dumps_with_payload({'a': 1})
        self.assertEqual(payload, pickle.dumps({'a': 1}))
        self.assertEqual(safe_pickle.unsign_bytes(blob), payload)

    def test_unsigned_payload_is_rejected(self):
        """A raw pickle -- what an attacker would write -- never reaches pickle."""
        with self.assertRaises(safe_pickle.UntrustedPayload):
            safe_pickle.loads(pickle.dumps({'a': 1}))

    def test_tampered_payload_is_rejected(self):
        blob = bytearray(safe_pickle.dumps({'a': 1}))
        blob[-1] ^= 0xFF
        with self.assertRaises(safe_pickle.UntrustedPayload):
            safe_pickle.loads(bytes(blob))

    def test_tampered_signature_is_rejected(self):
        blob = bytearray(safe_pickle.dumps({'a': 1}))
        blob[10] ^= 0xFF
        with self.assertRaises(safe_pickle.UntrustedPayload):
            safe_pickle.loads(bytes(blob))

    def test_empty_and_short_blobs_are_rejected(self):
        for blob in (b'', b'espsig1:', b'espsig1:short'):
            with self.assertRaises(safe_pickle.UntrustedPayload):
                safe_pickle.loads(blob)

    def test_reduce_gadget_does_not_execute(self):
        """The classic __reduce__ RCE payload is refused before unpickling."""
        class Exploit(object):
            def __reduce__(self):
                return (print, ('pwned',))

        with self.assertRaises(safe_pickle.UntrustedPayload):
            safe_pickle.loads(pickle.dumps(Exploit()))

    def test_salt_is_namespaced(self):
        """A blob signed for one field cannot be replayed into another."""
        blob = safe_pickle.dumps({'a': 1}, 'field.one')
        self.assertEqual(safe_pickle.loads(blob, 'field.one'), {'a': 1})
        with self.assertRaises(safe_pickle.UntrustedPayload):
            safe_pickle.loads(blob, 'field.two')

    def test_memoryview_input(self):
        """BinaryField columns can hand back a memoryview rather than bytes."""
        blob = safe_pickle.dumps({'a': 1})
        self.assertEqual(safe_pickle.loads(memoryview(blob)), {'a': 1})

    def test_secret_key_rotation_with_fallback(self):
        with override_settings(SECRET_KEY='old-key', SECRET_KEY_FALLBACKS=[]):
            blob = safe_pickle.dumps({'a': 1})
        with override_settings(SECRET_KEY='new-key', SECRET_KEY_FALLBACKS=['old-key']):
            self.assertEqual(safe_pickle.loads(blob), {'a': 1})
        with override_settings(SECRET_KEY='new-key', SECRET_KEY_FALLBACKS=[]):
            with self.assertRaises(safe_pickle.UntrustedPayload):
                safe_pickle.loads(blob)
