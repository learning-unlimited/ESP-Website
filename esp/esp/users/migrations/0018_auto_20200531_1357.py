# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_auto_20200503_1216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permission',
            name='permission_type',
            field=models.CharField(max_length=80, choices=[('Administer', 'Full administrative permissions'), ('View', 'Able to view a program'), ('Onsite', 'Access to onsite interfaces'), ('GradeOverride', 'Ignore grade ranges for studentreg'), ('OverrideFull', 'Register for a full program'), ('OverridePhaseZero', 'Bypass Phase Zero to proceed to other student reg modules'), ('Student Deadlines', (('Student', 'Basic student access'), ('Student/All', 'All student deadlines'), ('Student/Acknowledgement', 'Student acknowledgement'), ('Student/Applications', 'Apply for classes'), ('Student/Classes', 'Register for classes'), ('Student/Classes/Lunch', 'Register for lunch'), ('Student/Classes/Lottery', 'Enter the lottery'), ('Student/Classes/PhaseZero', 'Enter Phase Zero'), ('Student/Classes/Lottery/View', 'View lottery results'), ('Student/ExtraCosts', 'Extra costs page'), ('Student/MainPage', 'Registration mainpage'), ('Student/Confirm', 'Confirm registration'), ('Student/Cancel', 'Cancel registration'), ('Student/Removal', 'Remove class registrations after registration closes'), ('Student/Payment', 'Pay for a program'), ('Student/Profile', 'Set profile info'), ('Student/Survey', 'Access to survey'), ('Student/FormstackMedliab', 'Access to Formstack medical and liability form'), ('Student/Finaid', 'Access to financial aid application'), ('Student/Webapp', 'Access to student onsite webapp'))), ('Teacher Deadlines', (('Teacher', 'Basic teacher access'), ('Teacher/All', 'All teacher deadlines'), ('Teacher/Acknowledgement', 'Teacher acknowledgement'), ('Teacher/AppReview', "Review students' apps"), ('Teacher/Availability', 'Set availability'), ('Teacher/Catalog', 'Catalog'), ('Teacher/Classes', 'Classes'), ('Teacher/Classes/All', 'Classes/All'), ('Teacher/Classes/View', 'Classes/View'), ('Teacher/Classes/Edit', 'Classes/Edit'), ('Teacher/Classes/CancelReq', 'Request class cancellation'), ('Teacher/Classes/Coteachers', 'Add or remove coteachers'), ('Teacher/Classes/Create', 'Create classes of all types'), ('Teacher/Classes/Create/Class', 'Create standard classes'), ('Teacher/Classes/Create/OpenClass', 'Create open classes'), ('Teacher/Events', 'Teacher training signup'), ('Teacher/Quiz', 'Teacher quiz'), ('Teacher/MainPage', 'Registration mainpage'), ('Teacher/Survey', 'Teacher Survey'), ('Teacher/Profile', 'Set profile info'), ('Teacher/Survey', 'Access to survey'), ('Teacher/Webapp', 'Access to teacher onsite webapp'))), ('Volunteer Deadlines', (('Volunteer', 'Basic volunteer access'), ('Volunteer/Signup', 'Volunteer signup')))]),
        ),
        migrations.AlterField(
            model_name='record',
            name='event',
            field=models.CharField(max_length=80, choices=[('student_survey', 'Completed student survey'), ('teacher_survey', 'Completed teacher survey'), ('reg_confirmed', 'Confirmed registration'), ('attended', 'Attended program'), ('checked_out', 'Checked out of program'), ('conf_email', 'Was sent confirmation email'), ('teacher_quiz_done', 'Completed teacher quiz'), ('paid', 'Paid for program'), ('med', 'Submitted medical form'), ('med_bypass', 'Recieved medical bypass'), ('liab', 'Submitted liability form'), ('onsite', 'Registered for program onsite'), ('schedule_printed', 'Printed student schedule onsite'), ('teacheracknowledgement', 'Did teacher acknowledgement'), ('studentacknowledgement', 'Did student acknowledgement'), ('lunch_selected', 'Selected a lunch block'), ('extra_form_done', 'Filled out Custom Form'), ('extra_costs_done', 'Filled out Student Extra Costs Form'), ('donation_done', 'Filled out Donation Form'), ('waitlist', 'Waitlisted for a program'), ('interview', 'Teacher-interviewed for a program'), ('teacher_training', 'Attended teacher-training for a program'), ('teacher_checked_in', 'Teacher checked in for teaching on the day of the program'), ('twophase_reg_done', 'Completed two-phase registration')]),
        ),
    ]
