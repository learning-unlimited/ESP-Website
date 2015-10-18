# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0003_auto_20151017_2134'),
        ('program', '0002_auto_20151004_1715'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsection',
            name='locations',
            field=models.ManyToManyField(to='resources.Location', blank=True),
        ),
    ]
