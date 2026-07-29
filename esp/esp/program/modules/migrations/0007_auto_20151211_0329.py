# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0006_populate_program'),
    ]

    operations = [
        migrations.AlterField(
            model_name='classregmoduleinfo',
            name='program',
            field=models.OneToOneField(to='program.Program'),
        ),
        migrations.AlterField(
            model_name='studentclassregmoduleinfo',
            name='program',
            field=models.OneToOneField(to='program.Program'),
        ),
    ]
