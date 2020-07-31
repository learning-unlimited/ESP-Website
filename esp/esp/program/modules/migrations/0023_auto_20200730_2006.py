# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def set_my_defaults(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    old_pms = ProgramModule.objects.filter(handler="SurveyModule")
    if old_pms.exists():
        for pm in old_pms:
            if pm.module_type == "teach":
                pm.handler = "TeacherSurveyModule"
                pm.link_title = "Teacher Surveys"
            else:
                pm.handler = "StudentSurveyModule"
                pm.link_title = "Student Surveys"
            pm.seq = 9999
            pm.save()
        new_pm1 = ProgramModule.objects.get(handler="StudentSurveyModule")
        new_pm2 = ProgramModule.objects.get(handler="TeacherSurveyModule")
        ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
        for pmo in ProgramModuleObj.objects.filter(module__in=[new_pm1, new_pm2]):
            pmo.seq = 9999
            pmo.save()

def reverse_func(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    pms = ProgramModule.objects.filter(handler="StudentSurveyModule")
    if pms.count() == 1:
        new_pm1 = pms[0] if pms.count() == 1 else None
    pms = ProgramModule.objects.filter(handler="TeacherSurveyModule")
    if pms.count() == 1:
        new_pm2 = pms[0] if pms.count() == 1 else None
    for pm in [new_pm1, new_pm2]:
        pm.handler = "SurveyModule"
        pm.link_title = "Surveys"
        if "Teacher" in pm.admin_title:
            pm.seq = 15
        else:
            pm.seq = 20
        pm.save()
    old_pms = ProgramModule.objects.filter(handler="SurveyModule")
    ProgramModuleObj = apps.get_model('modules', 'ProgramModuleObj')
    for pmo in ProgramModuleObj.objects.filter(module__in=old_pms):
        if pmo.module.module_type == "learn":
            pmo.seq = 20
        else:
            pmo.seq = 15
        pmo.save()

class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0022_change_teacheronsite_seq'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentSurveyModule',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.CreateModel(
            name='TeacherSurveyModule',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.RunPython(set_my_defaults, reverse_func),
        migrations.DeleteModel(
            name='SurveyModule',
        ),
    ]
