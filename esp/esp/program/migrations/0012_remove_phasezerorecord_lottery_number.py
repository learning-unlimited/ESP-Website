# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0011_auto_20170109_1715'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='phasezerorecord',
            name='lottery_number',
        ),
    ]
