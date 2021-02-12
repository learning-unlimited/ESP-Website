# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def set_my_defaults(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    for pm in ProgramModule.objects.filter(handler="TeacherOnsite"):
        pm.seq = 9999
        pm.save()
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module=pm):
            pmo.seq = 9999
            pmo.save()

def reverse_func(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    for pm in ProgramModule.objects.filter(handler="TeacherOnsite"):
        pm.seq = -9999
        pm.save()
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module=pm):
            pmo.seq = -9999
            pmo.save()

class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0021_onsiteattendance_onsitecheckoutmodule_studentacknowledgementmodule_teacheronsite'),
    ]

    operations = [
        migrations.RunPython(set_my_defaults, reverse_func),
    ]
