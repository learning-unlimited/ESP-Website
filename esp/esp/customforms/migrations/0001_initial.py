# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attribute',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('attr_type', models.CharField(max_length=80)),
                ('value', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Field',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field_type', models.CharField(max_length=50)),
                ('seq', models.IntegerField()),
                ('label', models.CharField(max_length=200)),
                ('help_text', models.TextField(blank=True)),
                ('required', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Form',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=40, blank=True)),
                ('description', models.TextField(blank=True)),
                ('date_created', models.DateField(auto_now_add=True)),
                ('link_type', models.CharField(max_length=50, blank=True)),
                ('link_id', models.IntegerField(default=-1)),
                ('anonymous', models.BooleanField(default=False)),
                ('perms', models.CharField(max_length=200, blank=True)),
                ('success_message', models.CharField(max_length=500, blank=True)),
                ('success_url', models.CharField(max_length=200, blank=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('seq', models.IntegerField(default=-1)),
                ('form', models.ForeignKey(to='customforms.Form')),
            ],
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=40)),
                ('description', models.CharField(max_length=140, blank=True)),
                ('seq', models.IntegerField()),
                ('page', models.ForeignKey(to='customforms.Page')),
            ],
        ),
        migrations.AddField(
            model_name='field',
            name='form',
            field=models.ForeignKey(to='customforms.Form'),
        ),
        migrations.AddField(
            model_name='field',
            name='section',
            field=models.ForeignKey(to='customforms.Section'),
        ),
        migrations.AddField(
            model_name='attribute',
            name='field',
            field=models.ForeignKey(to='customforms.Field'),
        ),
    ]
