# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0009_cybersourcepostback'),
    ]

    operations = [
        migrations.AddField(
            model_name='lineitemoptions',
            name='is_custom',
            field=models.BooleanField(default=False),
        ),
    ]
