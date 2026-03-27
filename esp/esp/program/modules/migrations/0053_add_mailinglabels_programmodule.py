# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import migrations


def add_mailinglabels_module(apps, schema_editor):
    """Register MailingLabels in the ProgramModule table."""
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.get_or_create(
        handler='MailingLabels',
        defaults={
            'admin_title': 'Mailing Label Generation',
            'link_title': 'Generate Mailing Labels',
            'module_type': 'manage',
            'seq': 100,
            'choosable': 1,
        },
    )


def remove_mailinglabels_module(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.filter(handler='MailingLabels').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0052_admintestingmodule_batchclassregmodule'),
        ('program', '0013_auto_20200217_2130'),
    ]

    operations = [
        migrations.RunPython(add_mailinglabels_module, remove_mailinglabels_module),
    ]
