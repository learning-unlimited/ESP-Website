# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0006_transfer_paid_in'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='line_item',
            field=models.ForeignKey(to='accounting.LineItemType'),
        ),
    ]
