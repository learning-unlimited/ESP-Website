# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_auto_20161017_1848'),
        ('program', '0008_phasezerorecord'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='phasezerorecord',
            name='user',
        ),
        migrations.AddField(
            model_name='phasezerorecord',
            name='user',
            field=models.ManyToManyField(to='users.ESPUser'),
        ),
    ]
