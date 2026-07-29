# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0013_auto_20200503_1216'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsection',
            name='attending_students',
            field=models.IntegerField(default=0),
        ),
    ]
