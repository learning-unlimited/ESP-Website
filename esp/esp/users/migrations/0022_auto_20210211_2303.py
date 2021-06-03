# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_auto_20201013_2242'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactinfo',
            name='phone_cell',
            field=models.CharField(max_length=50, null=True, verbose_name=b'Cell phone', blank=True),
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='phone_day',
            field=models.CharField(max_length=50, null=True, verbose_name=b'Home phone', blank=True),
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='phone_even',
            field=models.CharField(max_length=50, null=True, verbose_name=b'Alternate phone', blank=True),
        ),
        migrations.AlterField(
            model_name='gradechangerequest',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='gradechangerequest',
            name='modified',
            field=django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True),
        ),
    ]
