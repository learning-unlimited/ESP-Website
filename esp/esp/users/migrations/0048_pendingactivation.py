"""Add PendingActivation, and clear the legacy activation keys.

Account activation used to append "_<key>" to the user's password hash and
treat the presence of that suffix as "this account is awaiting activation".
Activation tokens are now stateless HMACs (see esp.users.tokens), so nothing
is written to the password field any more and that signal disappears.

This migration does two things to the accounts still carrying a suffix:

1. Creates a PendingActivation row, which is the replacement signal.

2. Strips the suffix.

Stripping invalidates any pre-existing "?username=&key=" activation link,
since those were checked against the suffix.  Holders of one can use the
resend form (their PendingActivation row makes them eligible) or password
recovery, which also activates an inactive account.
"""

import datetime
import re

import django.db.models.deletion
from django.db import migrations, models


# Matches the legacy "_<key>" suffix, where <key> was random.randint(0, 2**31-1).
# Anchored at the end, and no hasher in use here emits an underscore after the
# first "$" (salts are [a-zA-Z0-9], digests are base64 or hex), so this cannot
# match an untouched password hash.
LEGACY_SUFFIX_REGEX = r'_\d+$'


BATCH_SIZE = 1000


def backfill_pending_activation(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    PendingActivation = apps.get_model('users', 'PendingActivation')

    pending = User.objects.filter(
        is_active=False,
        password__regex=LEGACY_SUFFIX_REGEX,
    ).exclude(password='emailuser')

    pks = list(pending.values_list('pk', flat=True))

    # Chunked in case there are a lot of accounts awaiting activation
    for start in range(0, len(pks), BATCH_SIZE):
        chunk = pks[start:start + BATCH_SIZE]

        PendingActivation.objects.bulk_create(
            [PendingActivation(user_id=pk) for pk in chunk],
            ignore_conflicts=True,
        )

        users = list(User.objects.filter(pk__in=chunk).only('pk', 'password'))
        for user in users:
            user.password = re.sub(LEGACY_SUFFIX_REGEX, '', user.password)
        User.objects.bulk_update(users, ['password'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0047_alter_permission_user_filter'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingActivation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(blank=True,
                                                 default=datetime.datetime.now)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pending_activation',
                    to='users.espuser')),
            ],
        ),
        migrations.RunPython(backfill_pending_activation,
                             reverse_code=migrations.RunPython.noop),
    ]
