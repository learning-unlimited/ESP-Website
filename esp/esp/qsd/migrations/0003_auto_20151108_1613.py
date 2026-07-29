# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qsd', '0002_auto_20151004_1715'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='quasistaticdata',
            options={'verbose_name': 'Editable'},
        ),
    ]
