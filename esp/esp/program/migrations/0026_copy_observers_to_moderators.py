# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def copy_observers_to_moderators(apps, schema_editor):
    """Copy rows from the old MIT classsection_observers table into
    classsection_moderators (LU's replacement field).  Skips pairs that
    already exist so the migration is safe to re-run."""
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


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0025_merge_20260316_2013'),
    ]

    operations = [
        migrations.RunPython(copy_observers_to_moderators, noop),
    ]
