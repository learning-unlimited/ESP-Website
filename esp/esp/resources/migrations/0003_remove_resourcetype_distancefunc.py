# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0002_resource_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resourcetype',
            name='distancefunc',
        ),
    ]
