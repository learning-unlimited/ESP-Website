# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FormstackAppSettings',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('form_id', models.IntegerField(null=True)),
                ('api_key', models.CharField(max_length=80)),
                ('finaid_form_id', models.IntegerField(null=True, blank=True)),
                ('username_field', models.IntegerField(null=True, blank=True)),
                ('coreclass_fields', models.CommaSeparatedIntegerField(help_text=b'A list of field ids separated by commas.', max_length=80, blank=True)),
                ('autopopulated_fields', models.TextField(help_text=b'To autopopulate fields on the form, type "[field id]: [Python\nexpression that returns field value]", one field per line. The Python\nexpression can use the variable \'user\' to refer to request.user.\n\nCaution: expressions will be eval()\'d by the server.', blank=True)),
                ('finaid_user_id_field', models.IntegerField(null=True, blank=True)),
                ('finaid_username_field', models.IntegerField(null=True, blank=True)),
                ('teacher_view_template', models.TextField(help_text=b'An HTML template for what teachers see when they view an app. To\ninclude the content of a field, use {{field.12345}} where 12345 is the\nfield id.', blank=True)),
                ('app_is_open', models.BooleanField(default=False, verbose_name=b'Application is currently open')),
            ],
        ),
        migrations.CreateModel(
            name='StudentClassApp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('student_preference', models.PositiveIntegerField()),
                ('teacher_rating', models.PositiveIntegerField(blank=True, null=True, choices=[(1, b'Green'), (2, b'Yellow'), (3, b'Red')])),
                ('teacher_ranking', models.PositiveIntegerField(null=True, blank=True)),
                ('teacher_comment', models.TextField(blank=True)),
                ('admission_status', models.IntegerField(default=0, choices=[(0, b'Unassigned'), (1, b'Admitted'), (2, b'Waitlist')])),
            ],
        ),
        migrations.CreateModel(
            name='StudentProgramApp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('admin_status', models.IntegerField(default=0, choices=[(0, b'Unreviewed'), (1, b'Approved'), (-1, b'Rejected')])),
                ('admin_comment', models.TextField(blank=True)),
                ('app_type', models.CharField(max_length=80, choices=[(b'Formstack', b'Formstack')])),
                ('submission_id', models.IntegerField(unique=True, null=True)),
            ],
        ),
    ]
