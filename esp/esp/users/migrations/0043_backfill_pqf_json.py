"""
Data migration: backfill q_filter_json from existing pickle blobs in PersistentQueryFilter.

Rows already populated (q_filter_json is not null) are skipped.
Rows whose pickle cannot be deserialised are skipped silently; they will
continue to use the pickle fallback path in get_Q().
"""

import pickle

from django.db import migrations
from django.db.models import Q


# ── helpers (duplicated here so the migration is self-contained) ──────────────

def _q_to_json(q_obj):
    """Recursively convert a Q object to a JSON-serialisable dict."""
    if not isinstance(q_obj, Q):
        # Leaf node: a tuple like ('field__lookup', value)
        return list(q_obj)
    return {
        'connector': q_obj.connector,
        'negated': q_obj.negated,
        'children': [_q_to_json(child) for child in q_obj.children],
    }


def migrate_pqf_data(apps, schema_editor):
    PQF = apps.get_model('users', 'PersistentQueryFilter')
    updated = 0
    skipped = 0

    for pqf in PQF.objects.filter(q_filter_json__isnull=True):
        if not pqf.q_filter:
            skipped += 1
            continue
        try:
            q_obj = pickle.loads(bytes(pqf.q_filter))
            pqf.q_filter_json = _q_to_json(q_obj)
            pqf.save(update_fields=['q_filter_json'])
            updated += 1
        except Exception:
            # Unpicklable row — leave it for the pickle fallback path.
            skipped += 1

    print(f"\n  PersistentQueryFilter backfill: {updated} migrated, {skipped} skipped")


def reverse_migration(apps, schema_editor):
    # Simply clear the JSON field; the pickle column is still intact.
    PQF = apps.get_model('users', 'PersistentQueryFilter')
    PQF.objects.update(q_filter_json=None)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0042_migrate_pqf_to_json'),
    ]

    operations = [
        migrations.RunPython(migrate_pqf_data, reverse_code=reverse_migration),
    ]
