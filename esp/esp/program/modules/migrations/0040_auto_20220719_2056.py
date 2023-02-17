# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-07-19 20:56
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0039_studentcertmodule'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentclassregmoduleinfo',
            name='priority_limit',
            field=models.IntegerField(default=3, help_text=b'The maximum number of choices a student can make per timeslot when priority registration is enabled. Also, the                                                                      number of priority slots listed in the rank classes interface for the two-phase student registration module.'),
        ),
        migrations.AlterField(
            model_name='studentclassregmoduleinfo',
            name='use_priority',
            field=models.BooleanField(default=False, help_text=b'Check this box to enable priority registration. Note, this is NOT for the two-phase student registration module. This will remove                                                                          the ability for students to enroll in classes during normal student registration (i.e., first-come first-served).'),
        ),
    ]
