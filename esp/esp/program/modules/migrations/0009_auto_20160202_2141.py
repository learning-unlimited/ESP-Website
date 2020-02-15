# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0008_auto_20151211_0349'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='programmoduleobj',
            unique_together=set([('program', 'module')]),
        ),
    ]
