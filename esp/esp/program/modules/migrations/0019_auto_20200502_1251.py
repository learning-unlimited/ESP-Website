# -*- coding: utf-8 -*-

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0018_studentonsite'),
    ]

    operations = [
        migrations.AlterField(
            model_name='programmoduleobj',
            name='required_label',
            field=models.CharField(default='', max_length=80, blank=True),
        ),
    ]
