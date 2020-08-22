# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0011_auto_20200614_1216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='financialaidgrant',
            name='finalized',
            field=models.BooleanField(default=False, editable=False),
        ),
    ]
