"""Data migration to rehash PersistentQueryFilter.sha1_hash from SHA-1 to SHA-256.

Existing rows store SHA-1 hashes in the sha1_hash column. After switching all
application code to hashlib.sha256(), we must rehash every row so that lookups
remain consistent.
"""

from django.db import migrations
import hashlib


def rehash_sha1_to_sha256(apps, schema_editor):
    PersistentQueryFilter = apps.get_model('users', 'PersistentQueryFilter')
    for pqf in PersistentQueryFilter.objects.all():
        pqf.sha1_hash = hashlib.sha256(bytes(pqf.q_filter)).hexdigest()
        pqf.save(update_fields=['sha1_hash'])


def rehash_sha256_to_sha1(apps, schema_editor):
    PersistentQueryFilter = apps.get_model('users', 'PersistentQueryFilter')
    for pqf in PersistentQueryFilter.objects.all():
        pqf.sha1_hash = hashlib.sha1(bytes(pqf.q_filter)).hexdigest()
        pqf.save(update_fields=['sha1_hash'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0043_auto_20260327_1528'),
    ]

    operations = [
        migrations.RunPython(rehash_sha1_to_sha256, rehash_sha256_to_sha1),
    ]
