# -*- coding: utf-8 -*-

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0001_initial'),
        ('application', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprogramapp',
            name='program',
            field=models.ForeignKey(to='program.Program', on_delete=models.CASCADE),
        ),
    ]
