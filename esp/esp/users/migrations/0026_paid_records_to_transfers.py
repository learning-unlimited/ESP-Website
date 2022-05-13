# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-02-08 20:48
from __future__ import unicode_literals

from django.db import migrations, models

from esp.accounting.controllers import IndividualAccountingController
from esp.program.models import Program
from esp.users.models import ESPUser

def set_my_defaults(apps, schema_editor):
    Record = apps.get_model('users', 'Record')
    Transfer = apps.get_model('accounting', 'Transfer')
    LineItemType = apps.get_model('accounting', 'LineItemType')
    Account = apps.get_model('accounting', 'Account')
    recs = Record.objects.filter(event="paid", program__isnull=False, user__isnull=False)
    for rec in recs:
        # Use normal imports to get amount_due
        prog = Program.objects.get(id=rec.program.id)
        user = ESPUser.objects.get(id=rec.user.id)
        iac = IndividualAccountingController(prog, user)
        amount_due = iac.amount_due()

        if amount_due:
            # Use migration imports to create payment
            payments_lit = LineItemType.objects.filter(program__id=rec.program.id, for_payments=True).order_by('-id')[0]
            target_account = Account.objects.get(name='receivable')
            Transfer.objects.create(source=None,
                                    destination=target_account,
                                    user=rec.user,
                                    line_item=payments_lit,
                                    amount_dec=amount_due,
                                    transaction_id="created from deprecated paid records")
    recs.delete()

def reverse_func(apps, schema_editor):
    Transfer = apps.get_model('accounting', 'Transfer')
    Record = apps.get_model('users', 'Record')
    tfs = Transfer.objects.filter(transaction_id="created from deprecated paid records")
    for tf in tfs:
        prog = Program.objects.get(id=tf.line_item.program.id)
        user = ESPUser.objects.get(id=tf.user.id)
        if IndividualAccountingController(prog, user).has_paid(in_full=True):
            Record.objects.get_or_create(user=tf.user, program=tf.line_item.program, event="paid")
    tfs.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0025_auto_20210617_0839'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permission',
            name='permission_type',
            field=models.CharField(choices=[(b'Administer', b'Full administrative permissions'), (b'View', b'Able to view a program'), (b'Onsite', b'Access to onsite interfaces'), (b'GradeOverride', b'Ignore grade ranges for studentreg'), (b'OverrideFull', b'Register for a full program'), (b'OverridePhaseZero', b'Bypass Phase Zero to proceed to other student reg modules'), (b'Student Deadlines', ((b'Student/All', b'All student deadlines'), (b'Student', b'Basic student access'), (b'Student/MainPage', b'Registration mainpage'), (b'Student/Profile', b'Set profile info'), (b'Student/Acknowledgement', b'Student acknowledgement'), (b'Student/FormstackMedliab', b'Access to Formstack medical and liability form'), (b'Student/PhaseZero', b'Enter Phase Zero'), (b'Student/Applications', b'Apply for classes'), (b'Student/Classes', b'Register for classes'), (b'Student/Classes/Lunch', b'Register for lunch'), (b'Student/Classes/Lottery', b'Enter the lottery'), (b'Student/Classes/Lottery/View', b'View lottery results'), (b'Student/Confirm', b'Confirm registration'), (b'Student/Cancel', b'Cancel registration'), (b'Student/Removal', b'Remove class registrations after registration closes'), (b'Student/Finaid', b'Access to financial aid application'), (b'Student/ExtraCosts', b'Extra costs page'), (b'Student/Payment', b'Pay for a program'), (b'Student/Webapp', b'Access to student onsite webapp'), (b'Student/Survey', b'Access to survey'))), (b'Teacher Deadlines', ((b'Teacher/All', b'All teacher deadlines'), (b'Teacher', b'Basic teacher access'), (b'Teacher/MainPage', b'Registration mainpage'), (b'Teacher/Profile', b'Set profile info'), (b'Teacher/Acknowledgement', b'Teacher acknowledgement'), (b'Teacher/Availability', b'Set availability'), (b'Teacher/Moderate', b'Fill out the moderator form'), (b'Teacher/Events', b'Teacher training signup'), (b'Teacher/Quiz', b'Teacher quiz'), (b'Teacher/Catalog', b'Catalog'), (b'Teacher/Classes/All', b'All classes deadlines'), (b'Teacher/Classes', b'Classes'), (b'Teacher/Classes/View', b'View registered classes'), (b'Teacher/Classes/Edit', b'Edit registered classes'), (b'Teacher/Classes/CancelReq', b'Request class cancellation'), (b'Teacher/Classes/Coteachers', b'Add or remove coteachers'), (b'Teacher/Classes/Create', b'Create classes of all types'), (b'Teacher/Classes/Create/Class', b'Create standard classes'), (b'Teacher/Classes/Create/OpenClass', b'Create open classes'), (b'Teacher/AppReview', b"Review students' apps"), (b'Teacher/Webapp', b'Access to teacher onsite webapp'), (b'Teacher/Survey', b'Access to survey'))), (b'Volunteer Deadlines', ((b'Volunteer', b'Basic volunteer access'), (b'Volunteer/Signup', b'Volunteer signup')))], max_length=80),
        ),
        migrations.RunPython(set_my_defaults, reverse_func),
    ]