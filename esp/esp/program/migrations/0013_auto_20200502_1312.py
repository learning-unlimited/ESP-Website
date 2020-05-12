# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0012_remove_phasezerorecord_lottery_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='director_cc_email',
            field=models.EmailField(default=b'', help_text=b'If set, automated outgoing mail (except class cancellations) will be sent to this address <i>instead of</i> the director email. Use this if you do not want to spam the director email with teacher class registration emails. Otherwise, leave this field blank.', max_length=75, blank=True),
        ),
        migrations.AlterField(
            model_name='program',
            name='director_confidential_email',
            field=models.EmailField(default=b'', help_text=b'If set, confidential emails such as financial aid applications will be sent to this address <i>instead of</i> the director email.', max_length=75, blank=True),
        ),
        migrations.AlterField(
            model_name='volunteeroffer',
            name='shirt_type',
            field=models.CharField(blank=True, max_length=20, null=True, choices=[(b'M', b'Straight cut'), (b'F', b'Fitted cut')]),
        ),
    ]
