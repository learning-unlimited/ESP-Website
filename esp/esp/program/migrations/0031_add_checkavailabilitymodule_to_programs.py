# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def add_checkavailability_to_programs(apps, schema_editor):
    """
    CheckAvailabilityModule (choosable=1, auto-added to new programs) was
    previously surfaced on existing programs via a duplicate manage-type entry
    in AvailabilityModule.module_properties(). That duplicate was removed in
    commit 6595d0451 to align with LU SR16. This migration backfills the
    proper CheckAvailabilityModule association for all programs that already
    have AvailabilityModule enabled.
    """
    Program = apps.get_model('program', 'Program')
    ProgramModule = apps.get_model('program', 'ProgramModule')

    try:
        check_avail = ProgramModule.objects.get(
            handler='CheckAvailabilityModule', module_type='manage'
        )
    except ProgramModule.DoesNotExist:
        # Module not yet registered (shouldn't happen after modules.0047, but be safe)
        return

    for program in Program.objects.filter(program_modules__handler='AvailabilityModule').distinct():
        program.program_modules.add(check_avail)


def remove_checkavailability_from_programs(apps, schema_editor):
    Program = apps.get_model('program', 'Program')
    ProgramModule = apps.get_model('program', 'ProgramModule')

    try:
        check_avail = ProgramModule.objects.get(
            handler='CheckAvailabilityModule', module_type='manage'
        )
    except ProgramModule.DoesNotExist:
        return

    for program in Program.objects.filter(program_modules=check_avail).distinct():
        program.program_modules.remove(check_avail)


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0030_remove_observers_py3_fixes'),
        ('modules', '0047_recreate_checkavailabilitymodule_py3_helptext'),
    ]

    operations = [
        migrations.RunPython(
            add_checkavailability_to_programs,
            remove_checkavailability_from_programs,
        ),
    ]
