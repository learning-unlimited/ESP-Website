# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def give_queue_ids(apps, schema_editor):
    """ Locations connected to a network printer get a ULID for that
    connection (a field default would give them all the same one). Their
    print server queues are remade under the new names the next time they
    print. """
    from esp.utils.models import new_ulid
    Printer = apps.get_model('utils', 'Printer')
    for printer in Printer.objects.filter(mode='network'):
        printer.queue_id = new_ulid()
        printer.save(update_fields=['queue_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0007_printrequest_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='printer',
            name='queue_id',
            field=models.CharField(blank=True, editable=False, max_length=26, null=True, unique=True),
        ),
        migrations.RunPython(give_queue_ids, migrations.RunPython.noop),
    ]
