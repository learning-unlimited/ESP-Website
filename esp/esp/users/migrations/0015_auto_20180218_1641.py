# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_auto_20180217_1243'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gradechangerequest',
            name='created',
            field=django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created'),
        ),
        migrations.AlterField(
            model_name='gradechangerequest',
            name='modified',
            field=django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified'),
        ),
        migrations.AlterField(
            model_name='record',
            name='event',
            field=models.CharField(max_length=80, choices=[(b'student_survey', b'Completed student survey'), (b'teacher_survey', b'Completed teacher survey'), (b'reg_confirmed', b'Confirmed registration'), (b'attended', b'Attended program'), (b'conf_email', b'Was sent confirmation email'), (b'teacher_quiz_done', b'Completed teacher quiz'), (b'paid', b'Paid for program'), (b'med', b'Submitted medical form'), (b'med_bypass', b'Recieved medical bypass'), (b'liab', b'Submitted liability form'), (b'onsite', b'Registered for program on-site'), (b'schedule_printed', b'Printed student schedule on-site'), (b'teacheracknowledgement', b'Did teacher acknowledgement'), (b'minorspolicyacknowledgement', b'Acknowledged minors policy'), (b'lunch_selected', b'Selected a lunch block'), (b'extra_form_done', b'Filled out Custom Form'), (b'extra_costs_done', b'Filled out Student Extra Costs Form'), (b'donation_done', b'Filled out Donation Form'), (b'waitlist', b'Waitlisted for a program'), (b'interview', b'Teacher-interviewed for a program'), (b'teacher_training', b'Attended teacher-training for a program'), (b'teacher_checked_in', b'Teacher checked in for teaching on the day of the program'), (b'twophase_reg_done', b'Completed two-phase registration')]),
        ),
    ]
