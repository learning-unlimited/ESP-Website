# -*- coding: utf-8 -*-

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customforms', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='form',
            name='created_by',
            field=models.ForeignKey(to='users.ESPUser', on_delete=models.CASCADE),
        ),
    ]
