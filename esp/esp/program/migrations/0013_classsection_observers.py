# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_auto_20180218_1641'),
        ('program', '0012_remove_phasezerorecord_lottery_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsection',
            name='observers',
            field=models.ManyToManyField(related_name='observing_sections', to='users.ESPUser'),
        ),
    ]
