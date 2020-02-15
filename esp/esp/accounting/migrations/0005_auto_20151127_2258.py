# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0004_remove_account_balance_dec'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='destination',
            field=models.ForeignKey(related_name='transfer_destination', blank=True, to='accounting.Account', help_text=b'Destination account; where the money is going to. Leave blank if this is a payment to an outsider.', null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='source',
            field=models.ForeignKey(related_name='transfer_source', blank=True, to='accounting.Account', help_text=b'Source account; where the money is coming from. Leave blank if this is a payment from outside.', null=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='transaction_id',
            field=models.TextField(default=b'', help_text=b'If this transfer is from a credit card transaction, stores the transaction ID number from the processor.', max_length=64, verbose_name=b'Transaction ID', blank=True),
        ),
    ]
