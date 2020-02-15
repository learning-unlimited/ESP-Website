# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cal', '0002_event_program'),
        ('program', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=80)),
                ('num_students', models.IntegerField(default=-1, blank=True)),
                ('group_id', models.IntegerField(default=-1)),
                ('is_unique', models.BooleanField(default=False)),
                ('event', models.ForeignKey(to='cal.Event')),
            ],
        ),
        migrations.CreateModel(
            name='ResourceAssignment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('lock_level', models.IntegerField(default=0)),
                ('resource', models.ForeignKey(to='resources.Resource')),
                ('target', models.ForeignKey(to='program.ClassSection', null=True)),
                ('target_subj', models.ForeignKey(to='program.ClassSubject', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ResourceGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='ResourceRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('desired_value', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='ResourceType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40)),
                ('description', models.TextField()),
                ('consumable', models.BooleanField(default=False)),
                ('priority_default', models.IntegerField(default=-1)),
                ('only_one', models.BooleanField(default=False, help_text=b'If set, in some cases, only allow adding one instance of this resource.')),
                ('attributes_pickled', models.TextField(default=b"Don't care", help_text=b'A pipe (|) delimited list of possible attribute values.', blank=True)),
                ('autocreated', models.BooleanField(default=False)),
                ('distancefunc', models.TextField(help_text=b'Enter python code that assumes <tt>r1</tt> and <tt>r2</tt> are resources with this type.', null=True, blank=True)),
                ('program', models.ForeignKey(blank=True, to='program.Program', null=True)),
            ],
        ),
        migrations.AddField(
            model_name='resourcerequest',
            name='res_type',
            field=models.ForeignKey(to='resources.ResourceType', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='resourcerequest',
            name='target',
            field=models.ForeignKey(to='program.ClassSection', null=True),
        ),
        migrations.AddField(
            model_name='resourcerequest',
            name='target_subj',
            field=models.ForeignKey(to='program.ClassSubject', null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='res_group',
            field=models.ForeignKey(blank=True, to='resources.ResourceGroup', null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='res_type',
            field=models.ForeignKey(to='resources.ResourceType', on_delete=django.db.models.deletion.PROTECT),
        ),
    ]
