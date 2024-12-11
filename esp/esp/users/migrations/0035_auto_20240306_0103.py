# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2024-03-06 01:03
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0034_auto_20230525_2024'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permission',
            name='permission_type',
            field=models.CharField(choices=[('Administer', 'Full administrative permissions'), ('View', 'Able to view a program'), ('Onsite', 'Access to onsite interfaces'), ('GradeOverride', 'Ignore grade ranges for studentreg'), ('OverrideFull', 'Register for a full program'), ('OverridePhaseZero', 'Bypass Phase Zero to proceed to other student reg modules'), ('Student Deadlines', (('Student/All', 'All student deadlines'), ('Student', 'Basic student access'), ('Student/MainPage', 'Registration mainpage'), ('Student/Profile', 'Set profile info'), ('Student/Acknowledgement', 'Student acknowledgement'), ('Student/FormstackMedliab', 'Access to Formstack medical and liability form'), ('Student/PhaseZero', 'Enter Phase Zero'), ('Student/Applications', 'Apply for classes'), ('Student/Classes', 'Register for classes'), ('Student/Classes/Lunch', 'Register for lunch'), ('Student/Classes/Lottery', 'Enter the lottery'), ('Student/Classes/Lottery/View', 'View lottery results'), ('Student/Confirm', 'Confirm registration'), ('Student/Cancel', 'Cancel registration'), ('Student/Removal', 'Remove class registrations after registration closes'), ('Student/Finaid', 'Access to financial aid application'), ('Student/ExtraCosts', 'Extra costs page'), ('Student/Payment', 'Pay for a program'), ('Student/Webapp', 'Access to student onsite webapp'), ('Student/Survey', 'Access to survey'))), ('Teacher Deadlines', (('Teacher/All', 'All teacher deadlines'), ('Teacher', 'Basic teacher access'), ('Teacher/MainPage', 'Registration mainpage'), ('Teacher/Profile', 'Set profile info'), ('Teacher/Acknowledgement', 'Teacher acknowledgement'), ('Teacher/Availability', 'Set availability'), ('Teacher/Moderate', 'Fill out the moderator form'), ('Teacher/Events', 'Teacher training signup'), ('Teacher/Quiz', 'Teacher quiz'), ('Teacher/Catalog', 'Catalog'), ('Teacher/Classes/All', 'All classes deadlines'), ('Teacher/Classes/View', 'View registered classes'), ('Teacher/Classes/Edit', 'Edit registered classes'), ('Teacher/Classes/CancelReq', 'Request class cancellation'), ('Teacher/Classes/Coteachers', 'Add or remove coteachers'), ('Teacher/Classes/Create', 'Create classes of all types'), ('Teacher/Classes/Create/Class', 'Create standard classes'), ('Teacher/Classes/Create/OpenClass', 'Create open classes'), ('Teacher/AppReview', "Review students' apps"), ('Teacher/Webapp', 'Access to teacher onsite webapp'), ('Teacher/Survey', 'Access to survey'))), ('Volunteer Deadlines', (('Volunteer', 'Basic volunteer access'), ('Volunteer/Signup', 'Volunteer signup')))], max_length=80),
        ),
        migrations.AlterField(
            model_name='recordtype',
            name='name',
            field=models.CharField(help_text='A unique short name for the record type', max_length=80, unique=True),
        ),
    ]
