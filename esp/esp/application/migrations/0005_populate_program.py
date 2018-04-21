# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


# This is kinda duplicated from modules 0006, but having migrations import
# things is a bit fragile.
def populate_program(apps, schema_editor):
    Program = apps.get_model("program", "Program")
    FormstackAppSettings = apps.get_model("application",
                                          "FormstackAppSettings")
    for program in Program.objects.all():
        fsass = FormstackAppSettings.objects.filter(module__program=program)
        if fsass:
            # The old getModuleExtension just looked at the first one, so
            # that's the one we'll keep around and update, and we'll delete
            # the others.  This module extension is new enough that there
            # wasn't any weird stuff in the DB already anyway.
            good_fsas = fsass[0]
            good_fsas.program = program
            good_fsas.save()
            for fsas in fsass[1:]:
                fsas.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0004_formstackappsettings_program'),
        ('program', '0004_auto_20151126_2220'),
    ]

    operations = [
        migrations.RunPython(populate_program, migrations.RunPython.noop)
    ]
