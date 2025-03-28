# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-03-27 10:19
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0026_teachermoderatormodule'),
    ]

    operations = [
        migrations.AddField(
            model_name='ajaxchangelogentry',
            name='assigned',
            field=models.NullBooleanField(),
        ),
        migrations.AddField(
            model_name='ajaxchangelogentry',
            name='is_moderator',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='ajaxchangelogentry',
            name='moderator',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
