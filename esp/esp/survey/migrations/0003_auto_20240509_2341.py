# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2024-05-09 23:41
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('survey', '0002_auto_20200301_1048'),
    ]

    operations = [
        migrations.AlterField(
            model_name='survey',
            name='category',
            field=models.CharField(choices=[('learn', 'learn'), ('teach', 'teach')], max_length=10),
        ),
    ]
