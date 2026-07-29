# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import models, migrations
import esp.web.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='NavBarCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('include_auto_links', models.BooleanField(default=False)),
                ('name', models.CharField(max_length=64)),
                ('path', models.CharField(default='', help_text='Matches the beginning of the URL (without the /).  Example: learn/splash', max_length=64)),
                ('long_explanation', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='NavBarEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sort_rank', models.IntegerField()),
                ('link', models.CharField(max_length=256, null=True, blank=True)),
                ('text', models.CharField(max_length=64)),
                ('indent', models.BooleanField(default=False)),
                ('category', models.ForeignKey(default=esp.web.models.default_navbarcategory, to='web.NavBarCategory')),
            ],
            options={
                'verbose_name_plural': 'Nav Bar Entries',
            },
        ),
    ]
