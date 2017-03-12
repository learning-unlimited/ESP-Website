# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20151226_2257'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherinfo',
            name='affiliation',
            field=models.CharField(max_length=100, blank=True),
        ),
    ]
