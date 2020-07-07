# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def set_my_defaults(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    pm = ProgramModule.objects.get_or_create(handler="TeacherOnsite")[0]
    pm.seq = 9999
    pm.save()

def reverse_func(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    pm = ProgramModule.objects.get_or_create(handler="TeacherOnsite")[0]
    pm.seq = -9999
    pm.save()

class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0021_onsiteattendance_onsitecheckoutmodule_studentacknowledgementmodule_teacheronsite'),
    ]

    operations = [
        migrations.RunPython(set_my_defaults, reverse_func),
    ]
