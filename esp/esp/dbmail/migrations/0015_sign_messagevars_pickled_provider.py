"""Sign the existing MessageVars.pickled_provider blobs.

New rows store their provider by reference in ``provider_info``; rows written
before that store a pickle, and ``MessageVars._get_provider()`` now refuses to
unpickle one unless it carries a valid HMAC signature.

As in ``users.0050``, the blobs are signed as opaque bytes -- nothing is
unpickled here -- so this migration cannot execute a payload a tampered row
contains, but it will happily sign one.  Audit ``dbmail_messagevars`` first if
tampering is suspected.
"""

from django.db import migrations

from esp.utils import safe_pickle

SALT = 'dbmail.MessageVars.pickled_provider'
BATCH_SIZE = 500


def _rewrite(apps, transform):
    MessageVars = apps.get_model('dbmail', 'MessageVars')
    batch = []
    qs = MessageVars.objects.only('id', 'pickled_provider')
    for mv in qs.iterator(chunk_size=BATCH_SIZE):
        if not mv.pickled_provider:
            continue
        new_value = transform(bytes(mv.pickled_provider))
        if new_value is None:
            continue
        mv.pickled_provider = new_value
        batch.append(mv)
        if len(batch) >= BATCH_SIZE:
            MessageVars.objects.bulk_update(batch, ['pickled_provider'])
            batch = []
    if batch:
        MessageVars.objects.bulk_update(batch, ['pickled_provider'])


def sign_providers(apps, schema_editor):
    def transform(blob):
        if safe_pickle.is_signed(blob):
            return None
        return safe_pickle.sign_bytes(blob, SALT)
    _rewrite(apps, transform)


def unsign_providers(apps, schema_editor):
    def transform(blob):
        if not safe_pickle.is_signed(blob):
            return None
        try:
            return safe_pickle.unsign_bytes(blob, SALT)
        except safe_pickle.UntrustedPayload:
            return None
    _rewrite(apps, transform)


class Migration(migrations.Migration):

    dependencies = [
        ('dbmail', '0014_messagevars_provider_info'),
    ]

    operations = [
        migrations.RunPython(sign_providers, reverse_code=unsign_providers),
    ]
