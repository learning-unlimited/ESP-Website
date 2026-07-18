"""
Data migration: backfill provider_info JSON from existing pickled_provider blobs
in MessageVars.

Rows already populated (provider_info is not null) are skipped.
Rows whose pickle cannot be deserialised, or whose class is not in the safe
registry, are skipped silently.
"""

import copyreg
import importlib
import io
import pickle

from django.db import migrations


# Safe registry of provider class names → (app_label, model_name) pairs.
# Only classes in this whitelist are migrated; anything else is skipped for
# manual remediation.
_SAFE_PROVIDERS = {
    'Program':              ('program', 'program'),
    'ClassSection':         ('program', 'classsection'),
    'ESPUser':              ('users', 'espuser'),
}


_SAFE_PROVIDER_CLASS_PATHS = {
    ('esp.program.models', 'Program'),
    ('esp.program.models.__init__', 'Program'),
    ('esp.program.models.class_', 'ClassSection'),
    ('esp.users.models', 'ESPUser'),
    ('esp.users.models.__init__', 'ESPUser'),
}


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        # Allow only explicitly whitelisted provider classes.
        if (module, name) in _SAFE_PROVIDER_CLASS_PATHS:
            mod = importlib.import_module(module)
            return getattr(mod, name)

        # Allow safe helpers needed to reconstruct Django model instances.
        if module == 'copyreg' and name == '_reconstructor':
            return copyreg._reconstructor
        if module == 'django.db.models.base' and name == 'ModelState':
            from django.db.models.base import ModelState
            return ModelState
        if module == 'builtins' and name in {'object', 'dict', 'list', 'tuple', 'set', 'frozenset'}:
            import builtins
            return getattr(builtins, name)

        raise pickle.UnpicklingError(
            f"Global '{module}.{name}' is not allowed in restricted unpickler"
        )


def _restricted_loads(data):
    return _RestrictedUnpickler(io.BytesIO(data)).load()


def migrate_messagevars_data(apps, schema_editor):
    MessageVars = apps.get_model('dbmail', 'MessageVars')
    updated = 0
    skipped = 0

    for mv in MessageVars.objects.filter(provider_info__isnull=True):
        if not mv.pickled_provider:
            skipped += 1
            continue
        try:
            provider = _restricted_loads(bytes(mv.pickled_provider))
            class_name = provider.__class__.__name__

            if class_name not in _SAFE_PROVIDERS:
                # Unknown provider class — skip for manual remediation.
                skipped += 1
                continue

            pk = getattr(provider, 'pk', None)
            if pk is None:
                skipped += 1
                continue

            mv.provider_info = {'class_name': class_name, 'pk': pk}
            mv.pickled_provider = None
            mv.save(update_fields=['provider_info', 'pickled_provider'])
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
