# -*- coding: utf-8 -*-

from django.db import migrations, models
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_zipcode_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactinfo',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True, on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='passwordrecoveryticket',
            name='user',
            field=models.ForeignKey(to='users.ESPUser', on_delete=models.CASCADE),
        ),
        migrations.AlterField(
            model_name='teacherinfo',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True, on_delete=models.CASCADE),
        ),
    ]
