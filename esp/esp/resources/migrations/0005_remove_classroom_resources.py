# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def remove_classrooms(apps, schema_editor):
    Resource = apps.get_model("resources", "Resource")
    if Resource.objects.filter(res_type__name='Classroom',
                               res_group__location__isnull=True).exists():
        raise Exception('This migration should be run immediately after 0004 '
                        'to avoid losing data.  Unfortunately, at this point '
                        "you'll probably have to manually migrate any "
                        'resources that changed in the meantime; take a look '
                        'at the source of migration 0004 for hints as to how '
                        'to do so.  Or reverse migration 0004 to throw away '
                        'the migrated data and start from scratch.')
    Resource.objects.filter(res_type__name='Classroom').delete()


# TODO: remove ResourceType Classroom too?


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0004_populate_locations'),
    ]

    operations = [
        # I'd really like to implement the reverse migration, but there are
        # enough weird edge cases that I don't think I could get it close
        # enough to right to be useful.  Load your old resources from a DB
        # dump, or do it manually, and good luck.  If you intend to be moving
        # back and forth a lot, just skip this migration for the moment; having
        # the old resources around probably won't hurt you.
        migrations.RunPython(remove_classrooms),
    ]
