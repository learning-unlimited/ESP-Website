# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-26 19:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_contactinfo_address_country'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='espuser',
            options={'verbose_name': 'ESP user'},
        ),
        migrations.AlterModelOptions(
            name='useravailability',
            options={'verbose_name_plural': 'User availabilities'},
        ),
        migrations.AlterModelOptions(
            name='zipcodesearches',
            options={'verbose_name_plural': 'Zip code searches'},
        ),
        migrations.AlterField(
            model_name='permission',
            name='permission_type',
            field=models.CharField(choices=[(b'Administer', b'Full administrative permissions'), (b'View', b'Able to view a program'), (b'Onsite', b'Access to onsite interfaces'), (b'GradeOverride', b'Ignore grade ranges for studentreg'), (b'OverrideFull', b'Register for a full program'), (b'OverridePhaseZero', b'Bypass Phase Zero to proceed to other student reg modules'), (b'Student Deadlines', ((b'Student', b'Basic student access'), (b'Student/All', b'All student deadlines'), (b'Student/Acknowledgement', b'Student acknowledgement'), (b'Student/Applications', b'Apply for classes'), (b'Student/Classes', b'Register for classes'), (b'Student/Classes/Lunch', b'Register for lunch'), (b'Student/Classes/Lottery', b'Enter the lottery'), (b'Student/Classes/PhaseZero', b'Enter Phase Zero'), (b'Student/Classes/Lottery/View', b'View lottery results'), (b'Student/ExtraCosts', b'Extra costs page'), (b'Student/MainPage', b'Registration mainpage'), (b'Student/Confirm', b'Confirm registration'), (b'Student/Cancel', b'Cancel registration'), (b'Student/Removal', b'Remove class registrations after registration closes'), (b'Student/Payment', b'Pay for a program'), (b'Student/Profile', b'Set profile info'), (b'Student/Survey', b'Access to survey'), (b'Student/FormstackMedliab', b'Access to Formstack medical and liability form'), (b'Student/Finaid', b'Access to financial aid application'), (b'Student/Webapp', b'Access to student onsite webapp'))), (b'Teacher Deadlines', ((b'Teacher', b'Basic teacher access'), (b'Teacher/All', b'All teacher deadlines'), (b'Teacher/Acknowledgement', b'Teacher acknowledgement'), (b'Teacher/AppReview', b"Review students' apps"), (b'Teacher/Availability', b'Set availability'), (b'Teacher/Moderate', b'Fill out the moderator form'), (b'Teacher/Catalog', b'Catalog'), (b'Teacher/Classes', b'Classes'), (b'Teacher/Classes/All', b'Classes/All'), (b'Teacher/Classes/View', b'Classes/View'), (b'Teacher/Classes/Edit', b'Classes/Edit'), (b'Teacher/Classes/CancelReq', b'Request class cancellation'), (b'Teacher/Classes/Coteachers', b'Add or remove coteachers'), (b'Teacher/Classes/Create', b'Create classes of all types'), (b'Teacher/Classes/Create/Class', b'Create standard classes'), (b'Teacher/Classes/Create/OpenClass', b'Create open classes'), (b'Teacher/Events', b'Teacher training signup'), (b'Teacher/Quiz', b'Teacher quiz'), (b'Teacher/MainPage', b'Registration mainpage'), (b'Teacher/Survey', b'Teacher Survey'), (b'Teacher/Profile', b'Set profile info'), (b'Teacher/Survey', b'Access to survey'), (b'Teacher/Webapp', b'Access to teacher onsite webapp'))), (b'Volunteer Deadlines', ((b'Volunteer', b'Basic volunteer access'), (b'Volunteer/Signup', b'Volunteer signup')))], max_length=80),
        ),
    ]
