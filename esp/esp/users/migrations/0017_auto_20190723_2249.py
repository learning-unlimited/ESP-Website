# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_auto_20180815_1642'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentinfo',
            name='shirt_type',
            field=models.CharField(blank=True, max_length=20, null=True, choices=[(b'M', b'Straight cut'), (b'F', b'Fitted cut')]),
        ),
        migrations.AlterField(
            model_name='teacherinfo',
            name='shirt_type',
            field=models.CharField(blank=True, max_length=20, null=True, choices=[(b'M', b'Straight cut'), (b'F', b'Fitted cut')]),
        ),
    ]
