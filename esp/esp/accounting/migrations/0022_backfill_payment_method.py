# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def backfill_payment_method(apps, schema_editor):
    """ Every payment recorded before payment methods were tracked is
    treated as a credit card payment. (Some were onsite cash/check payments
    marked with the check-in "paid" checkbox, but there's no record of which.)
    Payments are transfers from outside (no source account) for a payments
    line item. """
    Transfer = apps.get_model('accounting', 'Transfer')
    Transfer.objects.filter(
        source__isnull=True,
        line_item__for_payments=True,
        payment_method='',
    ).update(payment_method='card')


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0021_transfer_payment_method'),
    ]

    operations = [
        migrations.RunPython(backfill_payment_method, migrations.RunPython.noop),
    ]
