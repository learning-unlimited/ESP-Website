# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0003_default_print_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='printer',
            name='archived',
            field=models.BooleanField(default=False),
        ),
    ]
