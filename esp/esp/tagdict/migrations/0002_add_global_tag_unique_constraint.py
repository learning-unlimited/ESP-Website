# -*- coding: utf-8 -*-
"""
Migration to add a unique constraint for global tags (where content_type and object_id are both NULL).

This ensures that a tag key is unique when it's a global tag, preventing duplicate global tags
while still allowing multiple per-object tags with the same key.

The constraint is implemented using database-specific SQL since Django 2.2 doesn't fully support
conditional unique constraints via the ORM.
"""

from django.db import migrations, connection


def add_global_tag_constraint(apps, schema_editor):
    """
    Add a unique constraint for global tags based on the database backend.
    """
    vendor = connection.vendor
    
    if vendor == 'postgresql':
        # PostgreSQL: Use partial index (most efficient)
        schema_editor.execute(
            """
            CREATE UNIQUE INDEX tagdict_tag_unique_global
            ON tagdict_tag (key)
            WHERE content_type_id IS NULL AND object_id IS NULL;
            """
        )
    elif vendor == 'sqlite':
        # SQLite: Use partial index (supported in SQLite 3.8.0+, released 2013)
        schema_editor.execute(
            """
            CREATE UNIQUE INDEX tagdict_tag_unique_global
            ON tagdict_tag (key)
            WHERE content_type_id IS NULL AND object_id IS NULL;
            """
        )
    elif vendor == 'mysql':
        # MySQL: Use a workaround with a generated column and unique index
        # MySQL doesn't support partial indexes, so we create a computed column
        # that's NULL for non-global tags and equals the key for global tags
        schema_editor.execute(
            """
            ALTER TABLE tagdict_tag
            ADD COLUMN global_tag_key VARCHAR(50) AS (
                CASE
                    WHEN content_type_id IS NULL AND object_id IS NULL THEN `key`
                    ELSE NULL
                END
            ) STORED;
            """
        )
        schema_editor.execute(
            """
            CREATE UNIQUE INDEX tagdict_tag_unique_global
            ON tagdict_tag (global_tag_key);
            """
        )
    else:
        # For other databases, skip the constraint
        # Model-level validation will provide a fallback
        pass


def remove_global_tag_constraint(apps, schema_editor):
    """
    Remove the unique constraint for global tags.
    """
    vendor = connection.vendor
    
    if vendor in ('postgresql', 'sqlite'):
        schema_editor.execute(
            """
            DROP INDEX IF EXISTS tagdict_tag_unique_global;
            """
        )
    elif vendor == 'mysql':
        schema_editor.execute(
            """
            DROP INDEX tagdict_tag_unique_global ON tagdict_tag;
            """
        )
        schema_editor.execute(
            """
            ALTER TABLE tagdict_tag DROP COLUMN global_tag_key;
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ('tagdict', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            add_global_tag_constraint,
            reverse_code=remove_global_tag_constraint,
        ),
    ]
