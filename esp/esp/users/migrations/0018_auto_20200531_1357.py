# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_auto_20200503_1216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permission',
            name='permission_type',
            field=models.CharField(max_length=80, choices=[(b'Administer', b'Full administrative permissions'), (b'View', b'Able to view a program'), (b'Onsite', b'Access to onsite interfaces'), (b'GradeOverride', b'Ignore grade ranges for studentreg'), (b'OverrideFull', b'Register for a full program'), (b'OverridePhaseZero', b'Bypass Phase Zero to proceed to other student reg modules'), (b'Student Deadlines', ((b'Student', b'Basic student access'), (b'Student/All', b'All student deadlines'), (b'Student/Acknowledgement', b'Student acknowledgement'), (b'Student/Applications', b'Apply for classes'), (b'Student/Classes', b'Register for classes'), (b'Student/Classes/Lunch', b'Register for lunch'), (b'Student/Classes/Lottery', b'Enter the lottery'), (b'Student/Classes/PhaseZero', b'Enter Phase Zero'), (b'Student/Classes/Lottery/View', b'View lottery results'), (b'Student/ExtraCosts', b'Extra costs page'), (b'Student/MainPage', b'Registration mainpage'), (b'Student/Confirm', b'Confirm registration'), (b'Student/Cancel', b'Cancel registration'), (b'Student/Removal', b'Remove class registrations after registration closes'), (b'Student/Payment', b'Pay for a program'), (b'Student/Profile', b'Set profile info'), (b'Student/Survey', b'Access to survey'), (b'Student/FormstackMedliab', b'Access to Formstack medical and liability form'), (b'Student/Finaid', b'Access to financial aid application'), (b'Student/Webapp', b'Access to student onsite webapp'))), (b'Teacher Deadlines', ((b'Teacher', b'Basic teacher access'), (b'Teacher/All', b'All teacher deadlines'), (b'Teacher/Acknowledgement', b'Teacher acknowledgement'), (b'Teacher/AppReview', b"Review students' apps"), (b'Teacher/Availability', b'Set availability'), (b'Teacher/Catalog', b'Catalog'), (b'Teacher/Classes', b'Classes'), (b'Teacher/Classes/All', b'Classes/All'), (b'Teacher/Classes/View', b'Classes/View'), (b'Teacher/Classes/Edit', b'Classes/Edit'), (b'Teacher/Classes/CancelReq', b'Request class cancellation'), (b'Teacher/Classes/Coteachers', b'Add or remove coteachers'), (b'Teacher/Classes/Create', b'Create classes of all types'), (b'Teacher/Classes/Create/Class', b'Create standard classes'), (b'Teacher/Classes/Create/OpenClass', b'Create open classes'), (b'Teacher/Events', b'Teacher training signup'), (b'Teacher/Quiz', b'Teacher quiz'), (b'Teacher/MainPage', b'Registration mainpage'), (b'Teacher/Survey', b'Teacher Survey'), (b'Teacher/Profile', b'Set profile info'), (b'Teacher/Survey', b'Access to survey'), (b'Teacher/Webapp', b'Access to teacher onsite webapp'))), (b'Volunteer Deadlines', ((b'Volunteer', b'Basic volunteer access'), (b'Volunteer/Signup', b'Volunteer signup')))]),
        ),
        migrations.AlterField(
            model_name='record',
            name='event',
            field=models.CharField(max_length=80, choices=[(b'student_survey', b'Completed student survey'), (b'teacher_survey', b'Completed teacher survey'), (b'reg_confirmed', b'Confirmed registration'), (b'attended', b'Attended program'), (b'checked_out', b'Checked out of program'), (b'conf_email', b'Was sent confirmation email'), (b'teacher_quiz_done', b'Completed teacher quiz'), (b'paid', b'Paid for program'), (b'med', b'Submitted medical form'), (b'med_bypass', b'Recieved medical bypass'), (b'liab', b'Submitted liability form'), (b'onsite', b'Registered for program onsite'), (b'schedule_printed', b'Printed student schedule onsite'), (b'teacheracknowledgement', b'Did teacher acknowledgement'), (b'studentacknowledgement', b'Did student acknowledgement'), (b'lunch_selected', b'Selected a lunch block'), (b'extra_form_done', b'Filled out Custom Form'), (b'extra_costs_done', b'Filled out Student Extra Costs Form'), (b'donation_done', b'Filled out Donation Form'), (b'waitlist', b'Waitlisted for a program'), (b'interview', b'Teacher-interviewed for a program'), (b'teacher_training', b'Attended teacher-training for a program'), (b'teacher_checked_in', b'Teacher checked in for teaching on the day of the program'), (b'twophase_reg_done', b'Completed two-phase registration')]),
        ),
    ]
