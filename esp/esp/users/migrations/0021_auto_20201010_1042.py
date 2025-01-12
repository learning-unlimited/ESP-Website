# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-10-10 10:42
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations
import django.db.models.deletion
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_contactinfo_cleanup'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactinfo',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='users.ESPUser'),
        ),
    ]
