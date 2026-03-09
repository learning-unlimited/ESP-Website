# -*- coding: utf-8 -*-

from django.db import models, migrations
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0001_initial'),
        ('users', '0001_initial'),
        ('accounting', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transfer',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='lineitemtype',
            name='program',
            field=models.ForeignKey(to='program.Program', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='lineitemoptions',
            name='lineitem_type',
            field=models.ForeignKey(to='accounting.LineItemType', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='financialaidgrant',
            name='request',
            field=esp.db.fields.AjaxForeignKey(to='program.FinancialAidRequest', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='account',
            name='program',
            field=models.ForeignKey(blank=True, to='program.Program', null=True, on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='financialaidgrant',
            unique_together={('request',)},
        ),
        migrations.AlterUniqueTogether(
            name='account',
            unique_together={('name',)},
        ),
    ]
