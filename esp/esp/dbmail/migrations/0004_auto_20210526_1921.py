# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-26 19:21
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbmail', '0003_messagerequest_public'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='messagevars',
            options={'verbose_name_plural': 'Message variables'},
        ),
        migrations.AlterModelOptions(
            name='textofemail',
            options={'verbose_name_plural': 'Email texts'},
        ),
    ]
