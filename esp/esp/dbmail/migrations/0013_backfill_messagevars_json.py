"""
Data migration: backfill provider_info JSON from existing pickled_provider blobs
in MessageVars.

Rows already populated (provider_info is not null) are skipped.
Rows whose pickle cannot be deserialised, or whose class is not in the safe
registry, are skipped silently; they will continue to use the pickle fallback
path in _get_provider().
"""

import pickle

from django.db import migrations


# Safe registry of provider class names → (app_label, model_name) pairs.
# Only classes in this whitelist are migrated; anything else is left for the
# pickle fallback path (or discarded if the class no longer exists).
_SAFE_PROVIDERS = {
    'Program':              ('program', 'program'),
    'ClassSection':         ('program', 'classsection'),
    'ESPUser':              ('users', 'espuser'),
}


def migrate_messagevars_data(apps, schema_editor):
    MessageVars = apps.get_model('dbmail', 'MessageVars')
    updated = 0
    skipped = 0

    for mv in MessageVars.objects.filter(provider_info__isnull=True):
        if not mv.pickled_provider:
            skipped += 1
            continue
        try:
            provider = pickle.loads(bytes(mv.pickled_provider))
            class_name = provider.__class__.__name__

            if class_name not in _SAFE_PROVIDERS:
                # Unknown provider class — leave pickle fallback intact.
                skipped += 1
                continue

            pk = getattr(provider, 'pk', None)
            if pk is None:
                skipped += 1
                continue

            mv.provider_info = {'class_name': class_name, 'pk': pk}
            mv.save(update_fields=['provider_info'])
            updated += 1
        except Exception:
            skipped += 1

    print(f"\n  MessageVars backfill: {updated} migrated, {skipped} skipped")


def reverse_migration(apps, schema_editor):
    MessageVars = apps.get_model('dbmail', 'MessageVars')
    MessageVars.objects.update(provider_info=None)


class Migration(migrations.Migration):

    dependencies = [
        ('dbmail', '0012_add_messagevars_json_field'),
    ]

    operations = [
        migrations.RunPython(migrate_messagevars_data, reverse_code=reverse_migration),
    ]
