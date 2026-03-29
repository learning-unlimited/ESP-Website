# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import migrations


def add_onsite_admin_webapp(apps, schema_editor):
    """Register OnSiteAdminWebApp in the ProgramModule table."""
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.get_or_create(
        handler='OnSiteAdminWebApp',
        defaults={
            'admin_title': 'Admin Onsite Webapp',
            'link_title': 'Onsite Admin Dashboard',
            'module_type': 'onsite',
            'seq': 5,
            'choosable': 1,
        },
    )


def remove_onsite_admin_webapp(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.filter(handler='OnSiteAdminWebApp').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0047_add_admintestingmodule'),
        ('program', '0013_auto_20200217_2130'),
    ]

    operations = [
        migrations.RunPython(add_onsite_admin_webapp, remove_onsite_admin_webapp),
    ]
