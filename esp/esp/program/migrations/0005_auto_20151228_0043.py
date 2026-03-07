# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0004_auto_20151126_2220'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='program',
            options={'ordering': ('-id',)},
        ),
    ]
