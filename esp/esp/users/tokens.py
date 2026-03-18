from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    HMAC-signed, time-limited token for account activation.
    Automatically invalidated when is_active changes (i.e. after first use).
    Token is never stored in the database.

    In Django 2.2, tokens inherit Django's PASSWORD_RESET_TIMEOUT_DAYS setting
    (default: 3 days), ensuring activation links automatically expire.
    Override PASSWORD_RESET_TIMEOUT_DAYS in local_settings.py to adjust.
    For newer Django versions, the equivalent setting is PASSWORD_RESET_TIMEOUT
    (in seconds).
    """
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"


account_activation_token = AccountActivationTokenGenerator()
