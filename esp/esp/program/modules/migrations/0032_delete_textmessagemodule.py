# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-08-19 08:56
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0031_deactivationmodule'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TextMessageModule',
        ),
    ]
