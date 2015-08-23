# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('balance_dec', models.DecimalField(default=Decimal('0'), help_text=b'The difference between incoming and outgoing transfers that have been executed so far against this account.', max_digits=9, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='FinancialAidGrant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount_max_dec', models.DecimalField(help_text=b'Enter a number here to grant a dollar value of financial aid.  The grant will cover this amount or the full cost of the program, whichever is less.', null=True, max_digits=9, decimal_places=2, blank=True)),
                ('percent', models.PositiveIntegerField(help_text=b'Enter an integer between 0 and 100 here to grant a certain percentage discount to the program after the above dollar credit is applied.  0 means no additional discount, 100 means no payment required.', null=True, blank=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('finalized', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='LineItemOptions',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.TextField(help_text=b'You can include the cost as part of the description, which is helpful if the cost differs from the line item type.')),
                ('amount_dec', models.DecimalField(help_text=b'The cost of this option--leave blank to inherit from the line item type.', null=True, max_digits=9, decimal_places=2, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='LineItemType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField(help_text=b'A description of this line item.')),
                ('amount_dec', models.DecimalField(help_text=b'The cost of this line item.', null=True, max_digits=9, decimal_places=2, blank=True)),
                ('required', models.BooleanField(default=False)),
                ('max_quantity', models.PositiveIntegerField(default=1)),
                ('for_payments', models.BooleanField(default=False)),
                ('for_finaid', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount_dec', models.DecimalField(max_digits=9, decimal_places=2)),
                ('transaction_id', models.TextField(default=b'', help_text=b'If this transfer is from a credit card transaction, stores the transaction ID number from the processor.', max_length=64, verbose_name=b'credit card processor transaction ID number', blank=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('executed', models.BooleanField(default=False)),
                ('destination', models.ForeignKey(related_name='transfer_destination', blank=True, to='accounting.Account', help_text=b'Destination account; where the money is going to.  Leave blank if this is a payment to an outsider.', null=True)),
                ('line_item', models.ForeignKey(blank=True, to='accounting.LineItemType', null=True)),
                ('option', models.ForeignKey(blank=True, to='accounting.LineItemOptions', null=True)),
                ('source', models.ForeignKey(related_name='transfer_source', blank=True, to='accounting.Account', help_text=b'Source account; where the money is coming from.  Leave blank if this is a payment from outside.', null=True)),
            ],
        ),
    ]
