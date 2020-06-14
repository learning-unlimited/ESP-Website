# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0005_resourcetype_hidden'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourceassignment',
            name='returned',
            field=models.BooleanField(default=False),
        ),
    ]
