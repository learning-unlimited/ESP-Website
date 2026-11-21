# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

#   Titles the module has had by default (any case: sites' databases differ)
OLD_LINK = ('Automatically Print Schedules', 'Printers')
OLD_ADMIN = ('Automatically Print Schedules for Onsite Reg', 'Printers (Onsite Schedule and Receipt Printing)')
NEW = ('Printer Setup', 'Printer Setup (day-of print locations, printers and print jobs)')


def _matching(qs, field, titles):
    ids = []
    for module in qs:
        if (getattr(module, field) or '').lower() in [t.lower() for t in titles]:
            ids.append(module.id)
    return qs.filter(id__in=ids)


def retitle(apps, schema_editor):
    """ The onsite module's link now leads to the Printer Setup page.
    (manage.py update never changes existing modules' titles; a title a site
    changed itself is left alone.) """
    ProgramModule = apps.get_model('program', 'ProgramModule')
    modules = ProgramModule.objects.filter(handler='OnsitePrintSchedules')
    _matching(modules, 'link_title', OLD_LINK).update(link_title=NEW[0])
    _matching(modules, 'admin_title', OLD_ADMIN).update(admin_title=NEW[1])


def undo(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    modules = ProgramModule.objects.filter(handler='OnsitePrintSchedules')
    _matching(modules, 'link_title', NEW[:1]).update(link_title=OLD_LINK[0])
    _matching(modules, 'admin_title', NEW[1:]).update(admin_title=OLD_ADMIN[0])


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0035_treasury_models'),
    ]

    operations = [
        migrations.RunPython(retitle, undo),
    ]
