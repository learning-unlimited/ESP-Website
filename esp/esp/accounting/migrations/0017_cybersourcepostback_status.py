# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import django.db.models.deletion
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0016_auto_20220719_2114'),
        ('program', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cybersourcepostback',
            name='status',
            field=models.CharField(blank=True, choices=[('processed', 'Processed'), ('needs_review', 'Payment recorded; needs manual review'), ('not_paid', 'No payment (declined, cancelled, or error)'), ('review_hold', 'Held for review by the processor; may have been charged'), ('failed', 'Failed; payment not recorded')], default='', help_text='Blank for postbacks received before statuses were recorded.', max_length=20),
        ),
        migrations.AddField(
            model_name='cybersourcepostback',
            name='transaction_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='cybersourcepostback',
            name='status_detail',
            field=models.TextField(blank=True, default='', help_text='Why the postback needs attention, if it does.'),
        ),
        migrations.AddField(
            model_name='cybersourcepostback',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='cybersourcepostback',
            name='program',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='program.Program'),
        ),
    ]
