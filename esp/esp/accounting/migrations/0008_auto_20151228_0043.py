# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0007_auto_20151226_1648'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='lineitemtype',
            options={'ordering': ('-program_id',)},
        ),
    ]
