# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0004_resource_attribute_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcetype',
            name='hidden',
            field=models.BooleanField(default=False),
        ),
    ]
