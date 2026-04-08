# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def fix_options_trailing_pipe(apps, schema_editor):
    """
    DynamicForm.py removed the [:-1] slice when splitting options on '|'
    (commit dfaff3c04). Old code stored options with a trailing pipe
    (e.g. 'A|B|C|'); new code no longer strips the trailing empty element,
    so those values would render a spurious empty choice. Strip trailing pipes.
    """
    Attribute = apps.get_model('customforms', 'Attribute')
    for attr in Attribute.objects.filter(attr_type='options'):
        if attr.value.endswith('|'):
            attr.value = attr.value.rstrip('|')
            attr.save()


def fix_checkbox_correct_answer_separator(apps, schema_editor):
    """
    DynamicForm.py changed the correct_answer separator for checkboxes from
    comma to pipe (commit 37f10e1f5). Migrate existing comma-separated values.
    """
    Attribute = apps.get_model('customforms', 'Attribute')
    for attr in Attribute.objects.filter(
        attr_type='correct_answer',
        field__field_type='checkboxes',
    ):
        if ',' in attr.value and '|' not in attr.value:
            attr.value = attr.value.replace(',', '|')
            attr.save()


def migrate_forward(apps, schema_editor):
    fix_options_trailing_pipe(apps, schema_editor)
    fix_checkbox_correct_answer_separator(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('customforms', '0002_auto_20151109_0048'),
    ]

    operations = [
        migrations.RunPython(
            migrate_forward,
            migrations.RunPython.noop,
        ),
    ]
