# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0002_auto_20151004_1715'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transfer',
            name='executed',
        ),
    ]
