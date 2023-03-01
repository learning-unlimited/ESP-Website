# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permission',
            name='permission_type',
            field=models.CharField(max_length=80, choices=[('Administer', 'Full administrative permissions'), ('View', 'Able to view a program'), ('Onsite', 'Access to onsite interfaces'), ('GradeOverride', 'Ignore grade ranges for studentreg'), ('OverrideFull', 'Register for a full program'), ('OverridePhaseZero', 'Bypass Phase Zero to proceed to other student reg modules'), ('Student Deadlines', (('Student', 'Basic student access'), ('Student/All', 'All student deadlines'), ('Student/Applications', 'Apply for classes'), ('Student/Catalog', 'View the catalog'), ('Student/Classes', 'Register for classes'), ('Student/Classes/Lottery', 'Enter the lottery'), ('Student/Classes/PhaseZero', 'Enter Phase Zero'), ('Student/Classes/Lottery/View', 'View lottery results'), ('Student/ExtraCosts', 'Extra costs page'), ('Student/MainPage', 'Registration mainpage'), ('Student/Confirm', 'Confirm registration'), ('Student/Cancel', 'Cancel registration'), ('Student/Removal', 'Remove class registrations after registration closes'), ('Student/Payment', 'Pay for a program'), ('Student/Profile', 'Set profile info'), ('Student/Survey', 'Access to survey'), ('Student/FormstackMedliab', 'Access to Formstack medical and liability form'), ('Student/Finaid', 'Access to financial aid application'))), ('Teacher Deadlines', (('Teacher', 'Basic teacher access'), ('Teacher/All', 'All teacher deadlines'), ('Teacher/Acknowledgement', 'Teacher acknowledgement'), ('Teacher/AppReview', "Review students' apps"), ('Teacher/Availability', 'Set availability'), ('Teacher/Catalog', 'Catalog'), ('Teacher/Classes', 'Classes'), ('Teacher/Classes/All', 'Classes/All'), ('Teacher/Classes/View', 'Classes/View'), ('Teacher/Classes/Edit', 'Classes/Edit'), ('Teacher/Classes/CancelReq', 'Request class cancellation'), ('Teacher/Classes/Create', 'Create classes of all types'), ('Teacher/Classes/Create/Class', 'Create standard classes'), ('Teacher/Classes/Create/OpenClass', 'Create open classes'), ('Teacher/Events', 'Teacher training signup'), ('Teacher/Quiz', 'Teacher quiz'), ('Teacher/MainPage', 'Registration mainpage'), ('Teacher/Survey', 'Teacher Survey'), ('Teacher/Profile', 'Set profile info'), ('Teacher/Survey', 'Access to survey'))), ('Volunteer Deadlines', (('Volunteer', 'Basic volunteer access'), ('Volunteer/Signup', 'Volunteer signup')))]),
        ),
    ]
