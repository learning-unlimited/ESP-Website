# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2024-03-09 13:56
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0007_auto_20200608_1929'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resourcetype',
            old_name='attributes_pickled',
            new_name='attributes_dumped',
        ),
    ]