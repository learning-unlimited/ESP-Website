"""Remove the PasswordRecoveryTicket model.

Password recovery now uses Django's built-in PasswordResetTokenGenerator,
which computes tokens via HMAC and never stores them in the database.
This addresses the security concern in issue #1195 where plaintext
recover_key values were stored in the database.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0040_auto_20260106_2204'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PasswordRecoveryTicket',
        ),
    ]
