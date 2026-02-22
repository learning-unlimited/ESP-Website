# -*- coding: utf-8 -*-
"""Make ProgramModule customizable fields nullable.

Part of issue #1690: Updating program module properties.

Fields seq and required become nullable so that NULL means
"use the code default from the handler's module_properties()" and a
non-NULL value means a chapter has explicitly customized the field.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0030_auto_20260106_2204'),
    ]

    operations = [
        migrations.AlterField(
            model_name='programmodule',
            name='seq',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='programmodule',
            name='required',
            field=models.NullBooleanField(default=None),
        ),
    ]
