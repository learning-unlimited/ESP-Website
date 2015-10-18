# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0003_auto_20151017_2134'),
        ('cal', '0002_event_program'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='available_locations',
            field=models.ManyToManyField(to='resources.Location', blank=True),
        ),
    ]
