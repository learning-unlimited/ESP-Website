# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0002_resource_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'The name or room number', max_length=100)),
                ('capacity', models.IntegerField(help_text=b'The number of students the location can accommodate')),
                ('admin_notes', models.TextField(help_text=b'Notes on this classroom visible only to admins', blank=True)),
                ('teacher_notes', models.TextField(help_text=b"Notes on this classroom that will appear on teachers'schedules.", blank=True)),
                ('student_notes', models.TextField(help_text=b"Notes on this classroom that will appear on students'schedules.", blank=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='resourcetype',
            name='distancefunc',
        ),
        migrations.AddField(
            model_name='resourcegroup',
            name='location',
            field=models.ForeignKey(blank=True, to='resources.Location', null=True),
        ),
    ]
