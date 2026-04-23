"""
Cybersource HMAC-SHA256 signature utilities.

Used to verify incoming postbacks from Cybersource and to sign outgoing
form fields.  The algorithm follows Cybersource Secure Acceptance
documentation:

1. Read ``signed_field_names`` (comma-separated list of field names).
2. Build the data string ``key1=val1,key2=val2,...`` in that order.
3. Compute ``HMAC-SHA256(secret_key, data_string)``.
4. Base64-encode the result.
"""

import base64
import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def _build_data_to_sign(fields_dict, signed_field_names):
    """Return the comma-separated ``key=value`` string used as HMAC input."""
    return ','.join(
        '%s=%s' % (name, fields_dict.get(name, ''))
        for name in signed_field_names.split(',')
    )


def sign_fields(fields_dict, signed_field_names, secret_key):
    """Generate a Cybersource HMAC-SHA256 signature.

    Parameters
    ----------
    fields_dict : dict
        All form/POST fields (only those listed in *signed_field_names*
        are actually signed).
    signed_field_names : str
        Comma-separated list of field names to include in the signature.
    secret_key : str
        The shared HMAC secret from the Cybersource Secure Acceptance
        dashboard.

    Returns
    -------
    str
        Base64-encoded HMAC-SHA256 signature.
    """
    data_to_sign = _build_data_to_sign(fields_dict, signed_field_names)
    digest = hmac.new(
        secret_key.encode('utf-8'),
        data_to_sign.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode('utf-8')


def verify_cybersource_signature(post_data, secret_key):
    """Verify the HMAC-SHA256 signature on a Cybersource postback.

    Parameters
    ----------
    post_data : django.http.QueryDict or dict
        The POST data from the incoming request.
    secret_key : str
        The shared HMAC secret.

    Returns
    -------
    bool
        ``True`` if the signature is present and valid, ``False`` otherwise.
    """
    signature = post_data.get('signature')
    signed_field_names = post_data.get('signed_field_names')

    if not signature or not signed_field_names:
        logger.warning("Cybersource postback missing signature or signed_field_names")
        return False

    expected = sign_fields(post_data, signed_field_names, secret_key)
    return hmac.compare_digest(expected, signature)
