# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0008_printer_queue_id'),
        ('program', '0035_treasury_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='printer',
            name='last_ok_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='printrequest',
            name='deposit_slip',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='program.DepositSlip'),
        ),
        migrations.AddField(
            model_name='printrequest',
            name='document_json',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='printrequest',
            name='pages',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='printrequest',
            name='refusals',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='printrequest',
            name='refused_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='printrequest',
            name='kind',
            field=models.CharField(choices=[('schedule', 'Student schedule'), ('receipt', 'Receipt'), ('pdf', 'Uploaded PDF'), ('test', 'Test page'), ('qr', 'QR code'), ('deposit_slip', 'Deposit slip')], default='schedule', max_length=20),
        ),
    ]
