# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0038_merge_20260417_1508'),
    ]

    operations = [
        migrations.AlterField(
            model_name='printablejob',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.ESPUser'),
        ),
    ]
