# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-26 19:21
from __future__ import unicode_literals

from django.db import migrations
import django.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0022_auto_20210426_0906'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='classcategories',
            options={'verbose_name_plural': 'Class categories'},
        ),
        migrations.AlterModelOptions(
            name='scheduletestcategory',
            options={'verbose_name_plural': 'Schedule test categories'},
        ),
        migrations.AlterField(
            model_name='classsection',
            name='attending_students',
            field=django.db.models.fields.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='classsection',
            name='enrolled_students',
            field=django.db.models.fields.IntegerField(default=0),
        ),
    ]
