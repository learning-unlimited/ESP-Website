# -*- coding: utf-8 -*-
"""NULL out ProgramModule customizable fields that match code defaults.

Part of issue #1690: Updating program module properties.

For each ProgramModule row, compares link_title, seq, and required
against the code defaults from the handler's module_properties().
If they match, sets the field to NULL (meaning "use code default").
If they differ, keeps the value (chapter has explicitly customized it).

Code defaults are frozen at migration time so the migration is
deterministic and does not depend on runtime handler code.
"""

from django.db import migrations

# Frozen snapshot of (handler, module_type) -> {link_title, seq, required}
# generated from module_properties_autopopulated() at the time this migration
# was written.  Using a static dict keeps the migration deterministic and
# avoids importing handler code that may change in future commits.
CODE_DEFAULTS = {
    ('AJAXSchedulingModule', 'manage'): {'link_title': 'AJAX Scheduling', 'seq': 7, 'required': False},
    ('AccountingModule', 'manage'): {'link_title': 'Accounting', 'seq': 253, 'required': False},
    ('AdminClass', 'manage'): {'link_title': 'Manage Classes', 'seq': 1, 'required': False},
    ('AdminCore', 'manage'): {'link_title': 'Program Dashboard', 'seq': -9999, 'required': False},
    ('AdminMaterials', 'manage'): {'link_title': 'Manage Documents', 'seq': -9999, 'required': False},
    ('AdminReviewApps', 'manage'): {'link_title': 'Application Review for Admin', 'seq': 1000, 'required': False},
    ('AdminTestingModule', 'manage'): {'link_title': 'Testing Mode', 'seq': 35, 'required': False},
    ('AdminVitals', 'manage'): {'link_title': 'Program Vitals', 'seq': -2, 'required': False},
    ('AdmissionsDashboard', 'manage'): {'link_title': 'Admissions Dashboard', 'seq': 200, 'required': False},
    ('AdmissionsDashboard', 'teach'): {'link_title': 'Admissions Dashboard', 'seq': 200, 'required': False},
    ('AutoschedulerFrontendModule', 'manage'): {'link_title': 'Use the automatic scheduling tool', 'seq': 50, 'required': False},
    ('AvailabilityModule', 'teach'): {'link_title': 'Indicate Your Availability', 'seq': 1, 'required': True},
    ('BigBoardModule', 'manage'): {'link_title': 'Watch incoming student registrations', 'seq': 10, 'required': False},
    ('BulkCreateAccountModule', 'manage'): {'link_title': 'Bulk Create Accounts', 'seq': 10, 'required': False},
    ('CheckAvailabilityModule', 'manage'): {'link_title': 'Check Teacher Availability', 'seq': 0, 'required': False},
    ('ClassChangeRequestModule', 'learn'): {'link_title': 'Class Change Request', 'seq': 200, 'required': False},
    ('ClassFlagModule', 'manage'): {'link_title': 'Manage Class Flags', 'seq': 100, 'required': False},
    ('ClassSearchModule', 'manage'): {'link_title': 'Search for classes', 'seq': 10, 'required': False},
    ('CommModule', 'manage'): {'link_title': 'Communications Panel', 'seq': 10, 'required': False},
    ('CreditCardModule_Cybersource', 'learn'): {'link_title': 'Credit Card Payment', 'seq': 10000, 'required': False},
    ('CreditCardModule_Stripe', 'learn'): {'link_title': 'Credit Card Payment', 'seq': 10000, 'required': False},
    ('CreditCardViewer', 'manage'): {'link_title': 'View Credit Card Transactions', 'seq': 10000, 'required': False},
    ('DeactivationModule', 'manage'): {'link_title': 'Mass Deactivate Users', 'seq': 502, 'required': False},
    ('DonationModule', 'learn'): {'link_title': 'Optional Donation', 'seq': 50, 'required': False},
    ('FinAidApproveModule', 'manage'): {'link_title': 'Approve Financial Aid Requests', 'seq': 26, 'required': False},
    ('FinancialAidAppModule', 'learn'): {'link_title': 'Financial Aid Application', 'seq': 25, 'required': False},
    ('FormstackAppModule', 'learn'): {'link_title': 'Student Application', 'seq': 10, 'required': True},
    ('FormstackMedliabModule', 'learn'): {'link_title': 'Medical and Emergency Contact Information', 'seq': 3, 'required': True},
    ('GroupTextModule', 'manage'): {'link_title': 'Group Text Panel: Text all the students!', 'seq': 10, 'required': False},
    ('JSONDataModule', 'json'): {'link_title': 'JSON Data', 'seq': 0, 'required': False},
    ('LineItemsModule', 'manage'): {'link_title': 'Line Items Management', 'seq': -9999, 'required': False},
    ('ListGenModule', 'manage'): {'link_title': 'Generate List of Users', 'seq': 500, 'required': False},
    ('LotteryFrontendModule', 'manage'): {'link_title': 'Run the Lottery Assignment Thing', 'seq': 10, 'required': False},
    ('LotteryStudentRegModule', 'learn'): {'link_title': 'Class Registration Lottery', 'seq': 7, 'required': False},
    ('MailingLabels', 'manage'): {'link_title': 'Generate Mailing Labels', 'seq': 100, 'required': False},
    ('MapGenModule', 'manage'): {'link_title': 'Generate Map of Users', 'seq': 500, 'required': False},
    ('MedicalBypassModule', 'manage'): {'link_title': 'Grant Medliab Bypass', 'seq': 3, 'required': True},
    ('NameTagModule', 'manage'): {'link_title': 'Generate Nametags', 'seq': 100, 'required': False},
    ('OnSiteAttendance', 'onsite'): {'link_title': 'Check Student Attendance', 'seq': 1, 'required': False},
    ('OnSiteCheckinModule', 'onsite'): {'link_title': 'Check-in (check students off for payments and forms)', 'seq': 1, 'required': False},
    ('OnSiteCheckoutModule', 'onsite'): {'link_title': 'Check-out Students', 'seq': 1, 'required': False},
    ('OnSiteClassList', 'onsite'): {'link_title': 'List of Open Classes', 'seq': 32, 'required': False},
    ('OnSiteRegister', 'onsite'): {'link_title': 'New Student Registration', 'seq': 30, 'required': False},
    ('OnsiteClassSchedule', 'onsite'): {'link_title': 'Scheduling and Class Changes', 'seq': 30, 'required': False},
    ('OnsiteCore', 'onsite'): {'link_title': 'onsite', 'seq': -1000, 'required': False},
    ('OnsitePaidItemsModule', 'onsite'): {'link_title': 'View Purchased Items for a Student', 'seq': 31, 'required': False},
    ('OnsitePrintSchedules', 'onsite'): {'link_title': 'Automatically Print Schedules', 'seq': 10000, 'required': False},
    ('ProgramPrintables', 'manage'): {'link_title': 'Program Printables', 'seq': 5, 'required': False},
    ('RegProfileModule', 'learn'): {'link_title': 'Update Your Profile', 'seq': 0, 'required': True},
    ('RegProfileModule', 'teach'): {'link_title': 'Update Your Profile', 'seq': 0, 'required': True},
    ('ResourceModule', 'manage'): {'link_title': 'Manage Times and Rooms', 'seq': -99999, 'required': False},
    ('SchedulingCheckModule', 'manage'): {'link_title': 'Run Scheduling Diagnostics', 'seq': 10, 'required': False},
    ('StudentAcknowledgementModule', 'learn'): {'link_title': 'Student Acknowledgement', 'seq': 200, 'required': True},
    ('StudentCertModule', 'learn'): {'link_title': 'Print Completion Certificate', 'seq': 999999, 'required': False},
    ('StudentClassRegModule', 'learn'): {'link_title': 'Sign up for Classes', 'seq': 10, 'required': True},
    ('StudentCustomFormModule', 'learn'): {'link_title': 'Additional Student Information', 'seq': 4, 'required': False},
    ('StudentExtraCosts', 'learn'): {'link_title': 'T-Shirts, Meals, and Photos', 'seq': 30, 'required': False},
    ('StudentJunctionAppModule', 'learn'): {'link_title': 'Extra Application Info', 'seq': 10000, 'required': True},
    ('StudentLunchSelection', 'learn'): {'link_title': 'Select Lunch Period', 'seq': 5, 'required': True},
    ('StudentOnsite', 'learn'): {'link_title': 'Student Onsite', 'seq': 9999, 'required': False},
    ('StudentRegConfirm', 'learn'): {'link_title': 'Confirm Registration', 'seq': 99999, 'required': False},
    ('StudentRegCore', 'learn'): {'link_title': 'Student Registration', 'seq': -9999, 'required': False},
    ('StudentRegPhaseZero', 'learn'): {'link_title': 'Program Lottery Registration', 'seq': 2, 'required': True},
    ('StudentRegPhaseZeroManage', 'manage'): {'link_title': 'Manage Program Lottery', 'seq': 200, 'required': False},
    ('StudentRegTwoPhase', 'learn'): {'link_title': 'Two-Phase Student Registration', 'seq': 3, 'required': True},
    ('StudentSurveyModule', 'learn'): {'link_title': 'Student Surveys', 'seq': 9999, 'required': False},
    ('SurveyManagement', 'manage'): {'link_title': 'Surveys', 'seq': 25, 'required': False},
    ('TeacherAcknowledgementModule', 'teach'): {'link_title': 'Teacher Acknowledgement', 'seq': 200, 'required': True},
    ('TeacherBigBoardModule', 'manage'): {'link_title': 'Watch incoming teacher registrations', 'seq': 11, 'required': False},
    ('TeacherBioModule', 'teach'): {'link_title': 'Update your teacher biography', 'seq': -111, 'required': False},
    ('TeacherCheckinModule', 'onsite'): {'link_title': 'Check in teachers', 'seq': 10, 'required': False},
    ('TeacherClassRegModule', 'teach'): {'link_title': 'Register Your Classes', 'seq': 10, 'required': False},
    ('TeacherCustomFormModule', 'teach'): {'link_title': 'Additional Teacher Information', 'seq': 4, 'required': False},
    ('TeacherEventsManageModule', 'manage'): {'link_title': 'Teacher Training and Interviews', 'seq': 5, 'required': False},
    ('TeacherEventsModule', 'teach'): {'link_title': 'Sign up for Teacher Training and Interviews', 'seq': 5, 'required': False},
    ('TeacherModeratorModule', 'teach'): {'link_title': 'Moderator Signup', 'seq': 2, 'required': True},
    ('TeacherOnsite', 'teach'): {'link_title': 'Teacher Onsite', 'seq': 9999, 'required': False},
    ('TeacherPreviewModule', 'teach'): {'link_title': 'Preview Other Classes', 'seq': -10, 'required': False},
    ('TeacherQuizModule', 'teach'): {'link_title': 'Take the Teacher Logistics Quiz', 'seq': 5, 'required': False},
    ('TeacherRegCore', 'teach'): {'link_title': 'Teacher Registration', 'seq': -9999, 'required': False},
    ('TeacherReviewApps', 'teach'): {'link_title': 'Review Student Applications', 'seq': 1000, 'required': False},
    ('TeacherSurveyModule', 'teach'): {'link_title': 'Teacher Surveys', 'seq': 9999, 'required': False},
    ('UnenrollModule', 'onsite'): {'link_title': 'Unenroll Students', 'seq': 100, 'required': False},
    ('UserGroupModule', 'manage'): {'link_title': 'Manage User Groups', 'seq': 501, 'required': False},
    ('UserRecordsModule', 'manage'): {'link_title': 'Manage User Records', 'seq': 501, 'required': False},
    ('VolunteerManage', 'manage'): {'link_title': 'Manage Volunteers', 'seq': 0, 'required': False},
    ('VolunteerSignup', 'volunteer'): {'link_title': 'Sign Up to Volunteer', 'seq': 0, 'required': False},
}


def null_out_defaults(apps, schema_editor):
    """Set customizable fields to NULL where they match code defaults."""
    ProgramModule = apps.get_model('program', 'ProgramModule')

    for pm in ProgramModule.objects.all():
        key = (pm.handler, pm.module_type)
        if key not in CODE_DEFAULTS:
            continue
        defaults = CODE_DEFAULTS[key]
        changed = False

        # NULL out link_title if it matches code default
        code_link_title = defaults.get('link_title')
        if code_link_title is not None and pm.link_title == code_link_title:
            pm.link_title = None
            changed = True

        # NULL out seq if it matches code default
        code_seq = defaults.get('seq', 200)
        if pm.seq == code_seq:
            pm.seq = None
            changed = True

        # NULL out required if it matches code default
        code_required = defaults.get('required', False)
        if pm.required == code_required:
            pm.required = None
            changed = True

        if changed:
            pm.save()


def restore_defaults(apps, schema_editor):
    """Reverse migration: fill NULL fields back from code defaults."""
    ProgramModule = apps.get_model('program', 'ProgramModule')

    for pm in ProgramModule.objects.all():
        key = (pm.handler, pm.module_type)
        if key not in CODE_DEFAULTS:
            continue
        defaults = CODE_DEFAULTS[key]
        changed = False

        if pm.link_title is None:
            code_link_title = defaults.get('link_title')
            if code_link_title is not None:
                pm.link_title = code_link_title
                changed = True

        if pm.seq is None:
            pm.seq = defaults.get('seq', 200)
            changed = True

        if pm.required is None:
            pm.required = defaults.get('required', False)
            changed = True

        if changed:
            pm.save()


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0031_programmodule_nullable_customizable_fields'),
    ]

    operations = [
        migrations.RunPython(null_out_defaults, restore_defaults),
    ]
