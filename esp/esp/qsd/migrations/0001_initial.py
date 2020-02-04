# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='QuasiStaticData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(help_text=b'Full url, without the trailing .html', max_length=256)),
                ('name', models.SlugField(blank=True)),
                ('title', models.CharField(max_length=256)),
                ('content', models.TextField()),
                ('create_date', models.DateTimeField(default=datetime.datetime.now, verbose_name=b'last edited', editable=False)),
                ('disabled', models.BooleanField(default=False)),
                ('keywords', models.TextField(null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
            ],
        ),
    ]
