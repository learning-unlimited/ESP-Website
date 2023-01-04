# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0025_delete_checkavailabilitymodule'),
    ]

    operations = [
        migrations.AddField(
            model_name='classregmoduleinfo',
            name='class_min_duration',
            field=models.IntegerField(help_text=b'The minimum length of a class, in minutes. Typically set to 50 for HSSPs and left blank for Splarks.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='classregmoduleinfo',
            name='ask_for_room',
            field=models.BooleanField(default=False, help_text=b'If true, teachers will be asked if they have a particular classroom in mind.'),
        ),
        migrations.AlterField(
            model_name='classregmoduleinfo',
            name='class_max_duration',
            field=models.IntegerField(help_text=b'The maximum length of a class, in minutes. Typically set to 80 for HSSPs and 170 for Splarks.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='classregmoduleinfo',
            name='class_max_size',
            field=models.IntegerField(default=5, help_text=b'The maximum number of students a teacher can choose as their class capacity.', null=True),
        ),
        migrations.AlterField(
            model_name='classregmoduleinfo',
            name='class_min_cap',
            field=models.IntegerField(default=5, help_text=b'The minimum number of students a teacher can choose as their class capacity.', null=True),
        ),
        migrations.AlterField(
            model_name='classregmoduleinfo',
            name='class_other_sizes',
            field=models.CommaSeparatedIntegerField(default=b'7,10,12,15,20,30,50,75,100,150,200', max_length=100, null=True, help_text=b"Force the addition of these options to teachers' choices of class size.  (Enter a comma-separated list of integers.)"),
        ),
        migrations.AlterField(
            model_name='classregmoduleinfo',
            name='class_size_step',
            field=models.IntegerField(default=1, help_text=b'The interval for class capacity choices.', null=True),
        ),
        migrations.AlterField(
            model_name='classregmoduleinfo',
            name='open_class_registration',
            field=models.BooleanField(default=False, help_text=b'If true, teachers will be presented with an option to register for walk-in classes.'),
        ),
    ]
