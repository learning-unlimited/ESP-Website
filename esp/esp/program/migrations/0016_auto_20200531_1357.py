# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0015_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='programmodule',
            name='choosable',
            field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(2)]),
        ),
        migrations.AlterField(
            model_name='volunteeroffer',
            name='shirt_type',
            field=models.TextField(null=True, blank=True),
        ),
    ]
