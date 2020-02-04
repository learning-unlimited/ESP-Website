# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def populate_program(apps, schema_editor):
    Program = apps.get_model("program", "Program")
    for model_name in ["StudentClassRegModuleInfo", "ClassRegModuleInfo"]:
        ModuleInfo = apps.get_model("modules", model_name)
        for program in Program.objects.all():
            module_infos = ModuleInfo.objects.filter(module__program=program)
            if module_infos:
                # The old getModuleExtension just looked at the first one, so
                # that's the one we'll keep around and update, and we'll delete
                # the others.  (Actually, depending on how you called it,
                # getModuleExtension looked at either the first one, or the
                # first one that actually used the correct module.  I've
                # manually cleaned up the ones that didn't use the correct
                # module, and plus, having those in the first place was more or
                # less undefined behavior, and in practice most callers just
                # picked the first one, rather than the first one with the
                # correct module.)
                good_module_info = module_infos[0]
                good_module_info.program = program
                good_module_info.save()
                for module_info in module_infos[1:]:
                    module_info.delete()



class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0005_auto_20151211_0306'),
        ('program', '0004_auto_20151126_2220'),
    ]

    operations = [
        migrations.RunPython(populate_program, migrations.RunPython.noop),
    ]
