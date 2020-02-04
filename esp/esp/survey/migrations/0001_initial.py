# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField(null=True, blank=True)),
                ('value', models.TextField()),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('_param_values', models.TextField(help_text=b'A pipe (|) delimited list of values.', verbose_name=b'Parameter values', blank=True)),
                ('per_class', models.BooleanField(default=False)),
                ('seq', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['seq'],
            },
        ),
        migrations.CreateModel(
            name='QuestionType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('_param_names', models.TextField(help_text=b'A pipe (|) delimited list of parameter names.', verbose_name=b'Parameter names', blank=True)),
                ('is_numeric', models.BooleanField(default=False)),
                ('is_countable', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Survey',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('category', models.CharField(max_length=32)),
                ('program', models.ForeignKey(related_name='surveys', blank=True, to='program.Program', help_text=b'Blank if not associated to a program', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SurveyResponse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_filled', models.DateTimeField(default=datetime.datetime.now)),
                ('survey', models.ForeignKey(to='survey.Survey')),
            ],
        ),
        migrations.AddField(
            model_name='question',
            name='question_type',
            field=models.ForeignKey(to='survey.QuestionType'),
        ),
        migrations.AddField(
            model_name='question',
            name='survey',
            field=models.ForeignKey(related_name='questions', to='survey.Survey'),
        ),
        migrations.AddField(
            model_name='answer',
            name='question',
            field=models.ForeignKey(to='survey.Question'),
        ),
        migrations.AddField(
            model_name='answer',
            name='survey_response',
            field=models.ForeignKey(related_name='answers', to='survey.SurveyResponse'),
        ),
    ]
