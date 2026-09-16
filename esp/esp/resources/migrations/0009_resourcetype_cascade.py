# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0008_auto_20240309_1356'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resourcerequest',
            name='res_type',
            field=models.ForeignKey(on_delete=models.CASCADE, to='resources.ResourceType'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='res_type',
            field=models.ForeignKey(on_delete=models.CASCADE, to='resources.ResourceType'),
        ),
    ]
