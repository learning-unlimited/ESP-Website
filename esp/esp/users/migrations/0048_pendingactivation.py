"""Add PendingActivation and backfill it from the legacy password suffix.

Account activation used to append "_<key>" to the user's password hash and
treat the presence of that suffix as "this account is awaiting activation".
Activation tokens are now stateless HMACs (see esp.users.tokens), so nothing
is written to the password field any more and that signal disappears.

PendingActivation replaces it.  The backfill marks every account that is
currently inactive *and* still carries a legacy suffix, which is exactly the
set that was awaiting activation before this migration ran.  Accounts that
were deactivated on purpose have no suffix and are correctly left alone.
"""

import datetime

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
    ).exclude(password='emailuser').values_list('pk', flat=True)

    #   Chunked so the whole user table never has to fit in memory at once.
    batch = []
    for pk in pending.iterator(chunk_size=BATCH_SIZE):
        batch.append(PendingActivation(user_id=pk))
        if len(batch) >= BATCH_SIZE:
            PendingActivation.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        PendingActivation.objects.bulk_create(batch, ignore_conflicts=True)


def drop_pending_activation(apps, schema_editor):
    # The rows are derivable from the password suffix for legacy accounts, and
    # reversing past the model deletion below would drop them anyway.
    PendingActivation = apps.get_model('users', 'PendingActivation')
    PendingActivation.objects.all().delete()


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
                             drop_pending_activation),
    ]
