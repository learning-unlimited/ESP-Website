# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0012_remove_phasezerorecord_lottery_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='volunteeroffer',
            name='shirt_size',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='volunteeroffer',
            name='shirt_type',
            field=models.TextField(null=True, blank=True),
        ),
    ]
