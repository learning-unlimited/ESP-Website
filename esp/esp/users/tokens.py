from django.contrib.auth.tokens import PasswordResetTokenGenerator

from esp.users.models import PendingActivation


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    HMAC-signed, time-limited token for account activation.

    The token is never stored in the database: it is derived from the user's
    pk, the issue timestamp, and whether activation is still outstanding.  A
    database leak therefore cannot expose a usable activation link, which is
    the point of the exercise -- the old scheme kept a plaintext key in the
    password column.

    Tokens expire according to Django's PASSWORD_RESET_TIMEOUT setting
    (seconds; default 259200, i.e. 3 days).  Override it in local_settings.py
    to change how long activation links stay valid.
    """

    # Distinct from the parent's salt so activation tokens and password-reset
    # tokens are HMAC'd in separate domains rather than relying on their hash
    # inputs happening to differ.
    key_salt = "esp.users.tokens.AccountActivationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        # The pending-activation state makes the token single-use: activating
        # the account deletes the PendingActivation row, which changes the
        # hash and invalidates every link already issued.
        #
        # This is why the row is hashed rather than is_active.  is_active goes
        # back to False whenever an administrator disables an account, so
        # hashing it would let an unexpired link from before the deactivation
        # switch the account back on.  PendingActivation only ever goes from
        # set to cleared, so a spent token stays spent.
        #
        # The password hash is included for the same reason Django's own reset
        # tokens include it: registering again over a pending account resets
        # its password, and only the link from the most recent attempt should
        # still work.
        pending = PendingActivation.objects.filter(user_id=user.pk).exists()
        return f"{user.pk}{user.password}{timestamp}{pending}"


account_activation_token = AccountActivationTokenGenerator()
