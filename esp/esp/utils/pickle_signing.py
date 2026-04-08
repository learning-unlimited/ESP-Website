"""Secure pickle handling with HMAC-SHA256 signatures."""

import hmac
import hashlib
from django.conf import settings


def get_signing_key():
    """
    Get the secret key used for signing pickled data.

    Prefer a dedicated PICKLE_SIGNING_KEY setting; if it is not defined,
    derive a namespaced sub-key from Django's SECRET_KEY so that this
    protocol does not reuse the raw SECRET_KEY directly.
    """
    base_key = getattr(settings, "PICKLE_SIGNING_KEY", None)
    if base_key is None:
        base_key = settings.SECRET_KEY
    if isinstance(base_key, str):
        base_key = base_key.encode("utf-8")
    # Derive a protocol-specific key to avoid cross-protocol key reuse.
    return hmac.new(base_key, b"esp.utils.pickle_signing", hashlib.sha256).digest()
def sign_data(data):
    """Generate an HMAC-SHA256 signature for serialized data."""
    try:
        data_bytes = bytes(data)
    except TypeError:
        raise TypeError("Data must be bytes-like")
    key = get_signing_key()
    return hmac.new(key, data_bytes, hashlib.sha256).digest()


def verify_and_deserialize(data, signature, pickle_func):
    """Verify HMAC signature before deserializing pickled data."""
    try:
        data_bytes = bytes(data)
    except TypeError:
        raise TypeError("Data must be bytes-like")

    try:
        signature_bytes = bytes(signature)
    except TypeError:
        raise TypeError("Signature must be bytes-like")

    expected_signature = sign_data(data_bytes)
    if not hmac.compare_digest(signature_bytes, expected_signature):
        raise ValueError("Signature verification failed. Data may have been tampered with.")

    return pickle_func(data_bytes)
