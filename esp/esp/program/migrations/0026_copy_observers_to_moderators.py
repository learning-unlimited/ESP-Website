# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def copy_observers_to_moderators(apps, schema_editor):
    """Copy rows from the old MIT classsection_observers table into
    classsection_moderators (LU's replacement field).  Skips pairs that
    already exist so the migration is safe to re-run.  Also backfills the
    TeacherModeratorModule ("Moderator Signup") program module onto any
    program that had observers, since those programs relied on the old
    MIT-only observers feature without needing to enable the LU module."""
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO program_classsection_moderators (classsection_id, espuser_id)
            SELECT classsection_id, espuser_id
            FROM program_classsection_observers
            WHERE (classsection_id, espuser_id) NOT IN (
                SELECT classsection_id, espuser_id
                FROM program_classsection_moderators
            )
        """)

    # The TeacherModeratorModule ProgramModule row is normally created by
    # esp.program.modules.models.install(), which runs off the post_migrate
    # signal *after* the whole `migrate` command (including this migration)
    # completes -- so on a fresh database the row does not exist yet here.
    # get_or_create it with the same field values TeacherModeratorModule.
    # module_properties() specifies, so install() later finds this row (by
    # handler + module_type) instead of creating a duplicate.
    ProgramModule = apps.get_model('program', 'ProgramModule')
    moderator_module, _ = ProgramModule.objects.get_or_create(
        handler='TeacherModeratorModule',
        module_type='teach',
        defaults={
            'link_title': 'Moderator Signup',
            'admin_title': 'Moderator Signup',
            'required': True,
            'seq': 2,
            'choosable': 0,
        },
    )

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT cs.parent_program_id
            FROM program_classsection_observers obs
            JOIN program_classsection sec ON sec.id = obs.classsection_id
            JOIN program_class cs ON cs.id = sec.parent_class_id
        """)
        program_ids = [row[0] for row in cursor.fetchall()]

    Program = apps.get_model('program', 'Program')
    for program in Program.objects.filter(id__in=program_ids):
        program.program_modules.add(moderator_module)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0025_merge_20260316_2013'),
    ]

    operations = [
        migrations.RunPython(copy_observers_to_moderators, noop),
    ]
