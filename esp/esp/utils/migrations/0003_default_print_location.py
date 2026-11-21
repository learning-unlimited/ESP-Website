# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def forwards(apps, schema_editor):
    """ Creates the Default print location, points requests that named no
    printer at it, and marks old requests printed or (if they never were)
    cancelled, so they don't all print again when a printer connects. """
    Printer = apps.get_model('utils', 'Printer')
    PrintRequest = apps.get_model('utils', 'PrintRequest')
    default = Printer.objects.filter(is_default=True).first()
    if default is None:
        # Adopt a location already called Default (e.g. after rolling this
        # back and forward again, which loses is_default) instead of adding
        # a second one
        default = Printer.objects.filter(name='Default').order_by('id').first()
        if default is None:
            default = Printer.objects.create(name='Default', is_default=True)
        else:
            default.is_default = True
            default.save()
    PrintRequest.objects.filter(printer__isnull=True).update(printer=default)
    PrintRequest.objects.filter(time_executed__isnull=False).update(status='printed')
    PrintRequest.objects.filter(time_executed__isnull=True).update(status='cancelled')


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0002_dayof_printing'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
