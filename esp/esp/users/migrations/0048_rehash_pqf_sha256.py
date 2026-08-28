"""Rehash PersistentQueryFilter.sha1_hash from SHA-1 to SHA-256.

Existing rows store SHA-1 digests of the pickled Q object in the ``sha1_hash``
column.  Now that the application code hashes with ``hashlib.sha256()``, every
existing row has to be rehashed or lookups in
``PersistentQueryFilter.getFilterFromQ()`` would miss and silently create a
duplicate row for every filter that already exists.

The column itself is deliberately left named ``sha1_hash`` so that this stays a
data-only migration; renaming it would require a schema change and touching
every reference to the field.
"""

import hashlib

from django.db import migrations

#   Rows are read and written in chunks so that sites with a large
#   users_persistentqueryfilter table don't have to hold the whole thing in
#   memory at once.
BATCH_SIZE = 1000


def _rehash(apps, algorithm):
    PersistentQueryFilter = apps.get_model('users', 'PersistentQueryFilter')

    batch = []
    queryset = PersistentQueryFilter.objects.all().order_by('pk').iterator(
        chunk_size=BATCH_SIZE)
    for pqf in queryset:
        #   BinaryField comes back as memoryview on some backends and as bytes
        #   on others; normalize before hashing.  A row with no filter stored
        #   hashes the empty bytestring, which is what the application code
        #   does for an unpicklable Q object.
        q_filter = bytes(pqf.q_filter) if pqf.q_filter else b''
        pqf.sha1_hash = algorithm(q_filter).hexdigest()
        batch.append(pqf)
        if len(batch) >= BATCH_SIZE:
            PersistentQueryFilter.objects.bulk_update(batch, ['sha1_hash'])
            batch = []

    if batch:
        PersistentQueryFilter.objects.bulk_update(batch, ['sha1_hash'])


def rehash_sha1_to_sha256(apps, schema_editor):
    _rehash(apps, hashlib.sha256)


def rehash_sha256_to_sha1(apps, schema_editor):
    _rehash(apps, hashlib.sha1)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0047_alter_permission_user_filter'),
    ]

    operations = [
        migrations.RunPython(rehash_sha1_to_sha256, rehash_sha256_to_sha1),
    ]
