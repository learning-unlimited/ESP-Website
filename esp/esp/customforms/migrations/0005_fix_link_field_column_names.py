"""Rename misnamed linked-field columns in custom form response tables.

Before #3762 was fixed, adding a linked field to an existing form created its
foreign-key column as "link_<Model>" instead of "link_<Model>_id", which left
the form's responses unreadable.  Only that bug produces a "link_" column
without the "_id" suffix, so each one is renamed to what the model expects.
"""

import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def rename_link_columns(apps, schema_editor):
    connection = schema_editor.connection
    qn = connection.ops.quote_name
    with connection.cursor() as cursor:
        #   The customforms schema may not exist yet on a fresh database, in
        #   which case this finds nothing.
        cursor.execute("""
            SELECT table_name, column_name FROM information_schema.columns
            WHERE table_schema = 'customforms'
              AND table_name LIKE %s AND column_name LIKE %s AND column_name NOT LIKE %s
        """, [r'customforms\_response\_%', r'link\_%', r'%\_id'])
        misnamed = cursor.fetchall()
        for table, column in misnamed:
            cursor.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'customforms' AND table_name = %s AND column_name = %s
            """, [table, f'{column}_id'])
            if cursor.fetchone():
                logger.warning('Not renaming customforms.%s.%s: %s_id already exists',
                               table, column, column)
                continue
            cursor.execute(f'ALTER TABLE "customforms".{qn(table)} '
                           f'RENAME COLUMN {qn(column)} TO {qn(column + "_id")}')


class Migration(migrations.Migration):

    dependencies = [
        ('customforms', '0004_alter_field_options_alter_page_options_and_more'),
    ]

    operations = [
        migrations.RunPython(rename_link_columns, migrations.RunPython.noop),
    ]
