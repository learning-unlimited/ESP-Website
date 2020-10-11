# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0018_auto_20200828_1641'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsection',
            name='ever_checked_in_students',
            field=models.IntegerField(default=0),
        ),
    ]
