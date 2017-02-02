# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20160709_2038'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherinfo',
            name='affiliation',
            field=models.CharField(max_length=100, blank=True),
        ),
    ]
