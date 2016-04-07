# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Printer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'Name to display in onsite interface', max_length=255)),
                ('printer_type', models.CharField(max_length=255, blank=True)),
                ('notes', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='PrintRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_requested', models.DateTimeField(auto_now_add=True)),
                ('time_executed', models.DateTimeField(null=True, blank=True)),
                ('printer', models.ForeignKey(blank=True, to='utils.Printer', null=True)),
                ('user', esp.db.fields.AjaxForeignKey(to='users.ESPUser')),
            ],
        ),
        migrations.CreateModel(
            name='TemplateOverride',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'The filename (relative path) of the template to override.', max_length=255)),
                ('content', models.TextField()),
                ('version', models.IntegerField()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='templateoverride',
            unique_together=set([('name', 'version')]),
        ),
    ]
