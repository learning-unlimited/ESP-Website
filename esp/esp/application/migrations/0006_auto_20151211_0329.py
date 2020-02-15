# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0005_populate_program'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formstackappsettings',
            name='program',
            field=models.OneToOneField(to='program.Program'),
        ),
    ]
