"""Secure pickle handling with HMAC-SHA256 signatures."""

import hmac
import hashlib
from django.conf import settings


def get_signing_key():
    """Get the secret key used for signing pickled data."""
    return settings.SECRET_KEY.encode('utf-8')


def sign_data(data):
    """Generate an HMAC-SHA256 signature for serialized data."""
    if not isinstance(data, bytes):
        raise TypeError("Data must be bytes")
    key = get_signing_key()
    return hmac.new(key, data, hashlib.sha256).digest()


def verify_and_deserialize(data, signature, pickle_func):
    """Verify HMAC signature before deserializing pickled data."""
    if not isinstance(data, bytes):
        raise TypeError("Data must be bytes")
    if not isinstance(signature, bytes):
        raise TypeError("Signature must be bytes")

    expected_signature = sign_data(data)
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Signature verification failed. Data may have been tampered with.")

    return pickle_func(data)
