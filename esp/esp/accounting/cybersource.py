"""
Helpers for signing outgoing Cybersource Secure Acceptance requests and
verifying the authenticity of incoming postbacks, per Cybersource's
documented HMAC-SHA256 signing algorithm:

    https://developer.cybersource.com/docs/cybs/en-us/security-keys/...
    (Secure Acceptance: "Creating a Signature")

The algorithm, in both directions, is:

    data_to_sign = ",".join("%s=%s" % (name, fields[name])
                             for name in signed_field_names.split(","))
    signature = base64(hmac_sha256(secret_key, data_to_sign))

Only the fields listed in ``signed_field_names`` are included in, or
required to validate, the signature; ``unsigned_field_names`` lists any
other fields present but not covered by it.
"""
import base64
import hashlib
import hmac


def compute_signature(fields, signed_field_names, secret_key):
    """
    Compute the Cybersource Secure Acceptance signature for `fields` (a
    dict-like of field name -> string value), covering the fields named
    in `signed_field_names` (a comma-separated string, in order), using
    `secret_key` (the shared secret configured for the merchant profile).

    Returns the base64-encoded signature as a str.
    """
    data_to_sign = ','.join(
        '%s=%s' % (name, fields[name]) for name in signed_field_names.split(','))
    digest = hmac.new(
        secret_key.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(digest).decode('ascii')


def verify_signature(post_data, secret_key):
    """
    Verify an incoming Cybersource postback. `post_data` is a
    dict-like (e.g. a Django QueryDict) of the posted fields.

    Returns True only if:
      - `signed_field_names` and `signature` are both present,
      - every field listed in `signed_field_names` is present, and
      - the recomputed signature matches the one supplied, using a
        constant-time comparison.

    Any missing/malformed field is treated as a verification failure
    (returns False) rather than raising, so callers can fail closed
    without a separate existence check.
    """
    signed_field_names = post_data.get('signed_field_names')
    supplied_signature = post_data.get('signature')
    if not signed_field_names or not supplied_signature:
        return False
    try:
        expected_signature = compute_signature(post_data, signed_field_names, secret_key)
    except KeyError:
        # A field listed in signed_field_names was not actually posted.
        return False
    return hmac.compare_digest(expected_signature, supplied_signature)
