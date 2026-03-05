# -*- coding: utf-8 -*-
# Migration to convert file extensions to lowercase

from django.db import migrations
from django.core.management import call_command


def migrate_file_extensions(apps, schema_editor):
    """
    Run the lowercase_file_extensions management command to rename
    existing files with uppercase extensions to lowercase.
    """
    call_command('lowercase_file_extensions')


def reverse_migration(apps, schema_editor):
    """
    Reverse migration is not supported for this operation.
    This migration performs a one-way file system operation
    that cannot be easily reversed.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0002_auto_20210526_1921'),
    ]

    operations = [
        migrations.RunPython(migrate_file_extensions, reverse_migration),
    ]
