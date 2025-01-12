# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-03-18 09:42
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import django.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_contactinfo_address_country'),
        ('program', '0020_auto_20210317_2014'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsection',
            name='moderators',
            field=models.ManyToManyField(blank=True, related_name='moderating_sections', to='users.ESPUser'),
        ),
    ]
