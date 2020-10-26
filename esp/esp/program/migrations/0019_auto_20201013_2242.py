# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0018_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='volunteeroffer',
            name='shirt_type',
            field=models.TextField(null=True, blank=True),
        ),
    ]
