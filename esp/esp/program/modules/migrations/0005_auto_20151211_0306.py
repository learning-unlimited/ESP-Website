# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0004_auto_20151126_2220'),
        ('modules', '0004_delete_checklistmodule'),
    ]

    operations = [
        migrations.AddField(
            model_name='classregmoduleinfo',
            name='program',
            field=models.OneToOneField(null=True, to='program.Program'),
        ),
        migrations.AddField(
            model_name='studentclassregmoduleinfo',
            name='program',
            field=models.OneToOneField(null=True, to='program.Program'),
        ),
    ]
