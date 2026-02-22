# -*- coding: utf-8 -*-
"""NULL out ProgramModule customizable fields that match code defaults.

Part of issue #1690: Updating program module properties.

For each ProgramModule row, compares link_title, seq, and required
against the code defaults from the handler's module_properties().
If they match, sets the field to NULL (meaning "use code default").
If they differ, keeps the value (chapter has explicitly customized it).
"""

from django.db import migrations


def _build_code_defaults():
    """Build a mapping of (handler, module_type) -> properties dict."""
    from esp.program.modules import handlers
    modules = [x for x in handlers.__dict__.values()
               if hasattr(x, 'module_properties_autopopulated')]

    code_defaults = {}
    for module_cls in modules:
        try:
            for props in module_cls.module_properties_autopopulated():
                key = (props.get('handler'), props.get('module_type'))
                code_defaults[key] = props
        except Exception:
            continue
    return code_defaults


def null_out_defaults(apps, schema_editor):
    """Set customizable fields to NULL where they match code defaults."""
    ProgramModule = apps.get_model('program', 'ProgramModule')
    code_defaults = _build_code_defaults()

    for pm in ProgramModule.objects.all():
        key = (pm.handler, pm.module_type)
        if key not in code_defaults:
            continue
        defaults = code_defaults[key]
        changed = False

        # NULL out link_title if it matches code default
        code_link_title = defaults.get('link_title')
        if code_link_title is not None and pm.link_title == code_link_title:
            pm.link_title = None
            changed = True

        # NULL out seq if it matches code default
        code_seq = defaults.get('seq', 200)
        if pm.seq == code_seq:
            pm.seq = None
            changed = True

        # NULL out required if it matches code default
        code_required = defaults.get('required', False)
        if pm.required == code_required:
            pm.required = None
            changed = True

        if changed:
            pm.save()


def restore_defaults(apps, schema_editor):
    """Reverse migration: fill NULL fields back from code defaults."""
    ProgramModule = apps.get_model('program', 'ProgramModule')
    code_defaults = _build_code_defaults()

    for pm in ProgramModule.objects.all():
        key = (pm.handler, pm.module_type)
        if key not in code_defaults:
            continue
        defaults = code_defaults[key]
        changed = False

        if pm.link_title is None:
            code_link_title = defaults.get('link_title')
            if code_link_title is not None:
                pm.link_title = code_link_title
                changed = True

        if pm.seq is None:
            pm.seq = defaults.get('seq', 200)
            changed = True

        if pm.required is None:
            pm.required = defaults.get('required', False)
            changed = True

        if changed:
            pm.save()


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0031_programmodule_nullable_customizable_fields'),
    ]

    operations = [
        migrations.RunPython(null_out_defaults, restore_defaults),
    ]
