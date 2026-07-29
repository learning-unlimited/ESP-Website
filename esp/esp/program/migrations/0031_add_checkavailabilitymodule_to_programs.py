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

    # The CheckAvailabilityModule ProgramModule row is normally created by
    # esp.program.modules.models.install(), which runs off the post_migrate
    # signal *after* the whole `migrate` command (including this migration,
    # despite following modules.0047 in the dependency graph) completes -- so
    # on a fresh database the row does not exist yet here. get_or_create it
    # with the same field values CheckAvailabilityModule.module_properties()
    # specifies, so install() later finds this row (by handler + module_type)
    # instead of creating a duplicate.
    check_avail, _ = ProgramModule.objects.get_or_create(
        handler='CheckAvailabilityModule',
        module_type='manage',
        defaults={
            'link_title': 'Check Teacher Availability',
            'admin_title': 'Teacher Availability Checker',
            'seq': 0,
            'choosable': 1,
        },
    )

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
