from django.contrib.auth.tokens import PasswordResetTokenGenerator

from esp.users.models import PendingActivation


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    HMAC-signed, time-limited token for account activation.

    The token is derived from the user's pk, the issue timestamp, and whether
    activation is still outstanding

    Tokens expire according to Django's PASSWORD_RESET_TIMEOUT setting
    (seconds; default 259200, i.e. 3 days).
    """

    # Ensure activation tokens are distinct from password-reset tokens
    key_salt = "esp.users.tokens.AccountActivationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        # The pending-activation state makes the token single-use: activating
        # the account deletes the PendingActivation row, which changes the
        # hash and invalidates every link already issued.
        #
        # The password hash is included in case a user registers again and resets
        # their password; only the link from the most recent attempt should
        # still work.
        pending = PendingActivation.objects.filter(user_id=user.pk).exists()
        return f"{user.pk}{user.password}{timestamp}{pending}"


account_activation_token = AccountActivationTokenGenerator()
