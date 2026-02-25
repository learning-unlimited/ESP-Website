# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import migrations


def add_admin_testing_module(apps, schema_editor):
    """Register AdminTestingModule in the ProgramModule table."""
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.get_or_create(
        handler='AdminTestingModule',
        defaults={
            'admin_title': 'Admin Testing Mode',
            'link_title': 'Testing Mode',
            'module_type': 'manage',
            'seq': 35,
            'choosable': 1,
        },
    )


def remove_admin_testing_module(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.filter(handler='AdminTestingModule').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0046_auto_20260106_2204'),
    ]

    operations = [
        migrations.RunPython(add_admin_testing_module, remove_admin_testing_module),
    ]
