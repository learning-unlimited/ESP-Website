"""Authenticated (HMAC-signed) pickle payloads.

A few models store serialized Python objects in ``BinaryField`` columns.
``pickle.loads()`` executes arbitrary code during deserialization, so any
attacker able to write bytes into those columns (SQL injection, a stolen
admin/DB credential, a tampered backup) gets remote code execution the next
time the row is read.

This module removes that gadget by refusing to unpickle anything the
application did not write itself.  Every blob is prefixed with an HMAC-SHA256
tag keyed on ``settings.SECRET_KEY``; ``loads()`` verifies the tag *before*
handing the payload to ``pickle``.  Forging a tag requires the secret key, so
a row rewritten by an attacker fails verification and raises
``UntrustedPayload`` instead of executing.

Signing is done over raw bytes and verification never inspects the payload,
so existing blobs can be signed in a data migration without deserializing
them (see ``users.0050`` and ``dbmail.0015``).

Salts namespace the signature to a particular model field, so a blob cannot
be lifted from one column and replayed into another.

Note on key rotation: rotating ``SECRET_KEY`` invalidates every signature.
``SECRET_KEY_FALLBACKS`` is honored on verification, so the usual Django
rotation procedure (move the old key into ``SECRET_KEY_FALLBACKS``) keeps
existing rows readable; they are re-signed with the current key the next time
they are written.
"""

import hashlib
import hmac
import pickle

from django.conf import settings
from django.utils.encoding import force_bytes

__all__ = ('UntrustedPayload', 'dumps', 'dumps_with_payload', 'loads',
           'is_signed', 'sign_bytes', 'unsign_bytes')

#   Version prefix, so the format can be changed later without ambiguity.
_PREFIX = b'espsig1:'
_DIGEST = hashlib.sha256
_DIGEST_SIZE = _DIGEST().digest_size
_KEY_SALT = b'esp.utils.safe_pickle'


class UntrustedPayload(Exception):
    """Raised when a stored blob is missing or fails its signature check."""


def _keys():
    """Yield the signing key first, then any rotation fallbacks."""
    secrets = [settings.SECRET_KEY]
    secrets.extend(getattr(settings, 'SECRET_KEY_FALLBACKS', []) or [])
    for secret in secrets:
        yield hashlib.sha256(_KEY_SALT + force_bytes(secret)).digest()


def _tag(key, salt, payload):
    return hmac.new(key, force_bytes(salt) + b'\x00' + payload, _DIGEST).digest()


def is_signed(blob):
    """Whether ``blob`` carries a signature envelope (not that it is valid)."""
    if blob is None:
        return False
    blob = bytes(blob)
    return blob.startswith(_PREFIX) and len(blob) >= len(_PREFIX) + _DIGEST_SIZE


def sign_bytes(payload, salt=''):
    """Wrap already-serialized ``payload`` bytes in a signature envelope."""
    payload = bytes(payload)
    key = next(_keys())
    return _PREFIX + _tag(key, salt, payload) + payload


def unsign_bytes(blob, salt=''):
    """Return the payload of ``blob``, or raise ``UntrustedPayload``."""
    if not is_signed(blob):
        raise UntrustedPayload(
            'Stored payload is unsigned; it may predate the signing migration '
            'or have been written by something other than this application.'
        )
    blob = bytes(blob)
    offset = len(_PREFIX) + _DIGEST_SIZE
    signature, payload = blob[len(_PREFIX):offset], blob[offset:]
    for key in _keys():
        if hmac.compare_digest(signature, _tag(key, salt, payload)):
            return payload
    raise UntrustedPayload(
        'Stored payload failed its integrity check; it was not written by '
        'this application (or SECRET_KEY was rotated without a fallback).'
    )


def dumps_with_payload(obj, salt=''):
    """Return ``(signed_blob, raw_payload)`` for ``obj``.

    Callers that hash the serialized form (to deduplicate rows, say) want the
    raw payload rather than the envelope, so that the hashes they compute stay
    comparable with rows written before signing was introduced.
    """
    payload = pickle.dumps(obj)
    return sign_bytes(payload, salt), payload


def dumps(obj, salt=''):
    """Pickle ``obj`` and return a signed blob."""
    return dumps_with_payload(obj, salt)[0]


def loads(blob, salt=''):
    """Verify ``blob`` and unpickle it.  Raises ``UntrustedPayload`` if the
    signature is missing or wrong; ``pickle`` is never reached in that case."""
    return pickle.loads(unsign_bytes(blob, salt))
