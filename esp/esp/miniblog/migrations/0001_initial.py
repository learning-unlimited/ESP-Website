# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AnnouncementLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=256)),
                ('category', models.CharField(max_length=32)),
                ('timestamp', models.DateTimeField(default=datetime.datetime.now, editable=False)),
                ('highlight_begin', models.DateTimeField(help_text=b'When this should start being showcased.', null=True, blank=True)),
                ('highlight_expire', models.DateTimeField(help_text=b'When this should stop being showcased.', null=True, blank=True)),
                ('section', models.CharField(help_text=b"e.g. 'teach' or 'learn' or blank", max_length=32, null=True, blank=True)),
                ('href', models.URLField(help_text=b'The URL the link should point to.')),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('post_ts', models.DateTimeField(default=datetime.datetime.now, editable=False)),
                ('subject', models.CharField(max_length=256)),
                ('content', models.TextField(help_text=b'HTML not allowed.')),
            ],
            options={
                'ordering': ['-post_ts'],
            },
        ),
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=256)),
                ('slug', models.SlugField(default=b'General', help_text=b'(will determine the URL)')),
                ('timestamp', models.DateTimeField(default=datetime.datetime.now, editable=False)),
                ('highlight_begin', models.DateTimeField(help_text=b'When this should start being showcased.', null=True, blank=True)),
                ('highlight_expire', models.DateTimeField(help_text=b'When this should stop being showcased.', null=True, blank=True)),
                ('content', models.TextField(help_text=b'Yes, you can use markdown.')),
                ('sent', models.BooleanField(default=False, editable=False)),
                ('email', models.BooleanField(default=False, editable=False)),
                ('fromemail', models.CharField(max_length=80, null=True, editable=False, blank=True)),
                ('priority', models.IntegerField(null=True, blank=True)),
                ('section', models.CharField(help_text=b"e.g. 'teach' or 'learn' or blank", max_length=32, null=True, blank=True)),
            ],
            options={
                'ordering': ['-timestamp'],
                'verbose_name_plural': 'Entries',
            },
        ),
    ]
