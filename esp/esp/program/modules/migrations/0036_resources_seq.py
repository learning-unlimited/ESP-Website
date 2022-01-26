# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-12-14 21:05
from __future__ import unicode_literals

from django.db import migrations

def set_my_defaults(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    for pm in ProgramModule.objects.filter(handler="ResourceModule"):
        pm.seq = -99999
        pm.save()
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module=pm):
            pmo.seq = -99999
            pmo.save()

def reverse_func(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    for pm in ProgramModule.objects.filter(handler="ResourceModule"):
        pm.seq = 10
        pm.save()
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module=pm):
            pmo.seq = 10
            pmo.save()

class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0035_teachereventsmanagemodule'),
    ]

    operations = [
        migrations.RunPython(set_my_defaults, reverse_func),
    ]
