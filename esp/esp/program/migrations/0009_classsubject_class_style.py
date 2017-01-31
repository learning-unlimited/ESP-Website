# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0008_phasezerorecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsubject',
            name='class_style',
            field=models.TextField(null=True, blank=True),
        ),
    ]
