# -*- coding: utf-8 -*-

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0004_auto_20151126_2220'),
        ('application', '0003_auto_20151004_1715'),
    ]

    operations = [
        migrations.AddField(
            model_name='formstackappsettings',
            name='program',
            field=models.OneToOneField(null=True, to='program.Program', on_delete=models.CASCADE),
        ),
    ]
