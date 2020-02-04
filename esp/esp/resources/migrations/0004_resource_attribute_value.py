# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0003_remove_resourcetype_distancefunc'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='attribute_value',
            field=models.TextField(default=b'', blank=True),
        ),
    ]
