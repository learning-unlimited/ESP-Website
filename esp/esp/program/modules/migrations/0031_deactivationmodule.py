# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-08-01 11:07
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0030_usergroupmodule'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeactivationModule',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('modules.programmoduleobj',),
        ),
    ]
