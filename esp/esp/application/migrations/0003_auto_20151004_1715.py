# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0001_initial'),
        ('modules', '0002_auto_20151004_1715'),
        ('users', '0001_initial'),
        ('application', '0002_studentprogramapp_program'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprogramapp',
            name='user',
            field=models.ForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='studentclassapp',
            name='app',
            field=models.ForeignKey(to='application.StudentProgramApp'),
        ),
        migrations.AddField(
            model_name='studentclassapp',
            name='subject',
            field=models.ForeignKey(to='program.ClassSubject'),
        ),
        migrations.AddField(
            model_name='formstackappsettings',
            name='module',
            field=models.ForeignKey(to='modules.ProgramModuleObj'),
        ),
        migrations.CreateModel(
            name='FormstackStudentClassApp',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('application.studentclassapp',),
        ),
        migrations.CreateModel(
            name='FormstackStudentProgramApp',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('application.studentprogramapp',),
        ),
        migrations.AlterUniqueTogether(
            name='studentclassapp',
            unique_together=set([('app', 'student_preference')]),
        ),
    ]
