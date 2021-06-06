# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0019_auto_20201013_2242'),
    ]

    operations = [
        migrations.AlterField(
            model_name='volunteeroffer',
            name='phone',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
    ]
