"""Sign the existing PersistentQueryFilter.q_filter pickle blobs.

``PersistentQueryFilter.get_Q()`` now refuses to unpickle a blob unless it
carries a valid HMAC signature, so rows written before that change have to be
signed here or they would stop loading.

The blobs are signed as opaque bytes -- this migration never calls
``pickle.loads()``, so running it cannot execute anything a tampered row
contains.  Note the corollary: if the database was already compromised before
this runs, the malicious payload gets signed along with everything else.
Deployments that suspect tampering should audit ``users_persistentqueryfilter``
before migrating.
"""

from django.db import migrations

from esp.utils import safe_pickle

SALT = 'users.PersistentQueryFilter.q_filter'
BATCH_SIZE = 500


def _rewrite(apps, transform):
    PQF = apps.get_model('users', 'PersistentQueryFilter')
    batch, changed = [], 0
    for pqf in PQF.objects.only('id', 'q_filter').iterator(chunk_size=BATCH_SIZE):
        if not pqf.q_filter:
            continue
        new_value = transform(bytes(pqf.q_filter))
        if new_value is None:
            continue
        pqf.q_filter = new_value
        batch.append(pqf)
        if len(batch) >= BATCH_SIZE:
            PQF.objects.bulk_update(batch, ['q_filter'])
            changed += len(batch)
            batch = []
    if batch:
        PQF.objects.bulk_update(batch, ['q_filter'])
        changed += len(batch)
    return changed


def sign_filters(apps, schema_editor):
    def transform(blob):
        if safe_pickle.is_signed(blob):
            return None
        return safe_pickle.sign_bytes(blob, SALT)
    _rewrite(apps, transform)


def unsign_filters(apps, schema_editor):
    def transform(blob):
        if not safe_pickle.is_signed(blob):
            return None
        try:
            return safe_pickle.unsign_bytes(blob, SALT)
        except safe_pickle.UntrustedPayload:
            #   Not ours to unwrap; leave it alone.
            return None
    _rewrite(apps, transform)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0049_alter_permission_permission_type'),
    ]

    operations = [
        migrations.RunPython(sign_filters, reverse_code=unsign_filters),
    ]
