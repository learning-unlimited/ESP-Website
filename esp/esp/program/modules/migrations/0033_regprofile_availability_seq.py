# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-10-28 11:41
from __future__ import unicode_literals

from django.db import migrations

def set_my_defaults(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    for pm in ProgramModule.objects.filter(handler="RegProfileModule"):
        pm.seq = 0
        pm.save()
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module=pm):
            pmo.seq = 0
            pmo.save()
    for pm in ProgramModule.objects.filter(handler="AvailabilityModule"):
        pm.seq = 1
        pm.save()
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module=pm):
            pmo.seq = 1
            pmo.save()

def reverse_func(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    for pm in ProgramModule.objects.filter(handler="RegProfileModule"):
        pm.seq = 1
        pm.save()
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module=pm):
            pmo.seq = 1
            pmo.save()
    for pm in ProgramModule.objects.filter(handler="AvailabilityModule"):
        pm.seq = 0
        pm.save()
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module=pm):
            pmo.seq = 0
            pmo.save()

class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0032_delete_textmessagemodule'),
    ]

    operations = [
        migrations.RunPython(set_my_defaults, reverse_func),
    ]
