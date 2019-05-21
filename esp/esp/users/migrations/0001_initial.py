# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import esp.customforms.linkfields
import esp.db.fields
import django_extensions.db.fields
import localflavor.us.models
import django.contrib.auth.models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cal', '0002_event_program'),
        ('program', '0001_initial'),
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=64)),
                ('last_name', models.CharField(max_length=64)),
                ('e_mail', models.EmailField(max_length=75, null=True, verbose_name=b'Email address', blank=True)),
                ('phone_day', localflavor.us.models.PhoneNumberField(max_length=20, null=True, verbose_name=b'Home phone', blank=True)),
                ('phone_cell', localflavor.us.models.PhoneNumberField(max_length=20, null=True, verbose_name=b'Cell phone', blank=True)),
                ('receive_txt_message', models.BooleanField(default=False)),
                ('phone_even', localflavor.us.models.PhoneNumberField(max_length=20, null=True, verbose_name=b'Alternate phone', blank=True)),
                ('address_street', models.CharField(max_length=100, null=True, verbose_name=b'Street address', blank=True)),
                ('address_city', models.CharField(max_length=50, null=True, verbose_name=b'City', blank=True)),
                ('address_state', localflavor.us.models.USStateField(blank=True, max_length=2, null=True, verbose_name=b'State', choices=[(b'AL', b'Alabama'), (b'AK', b'Alaska'), (b'AS', b'American Samoa'), (b'AZ', b'Arizona'), (b'AR', b'Arkansas'), (b'AA', b'Armed Forces Americas'), (b'AE', b'Armed Forces Europe'), (b'AP', b'Armed Forces Pacific'), (b'CA', b'California'), (b'CO', b'Colorado'), (b'CT', b'Connecticut'), (b'DE', b'Delaware'), (b'DC', b'District of Columbia'), (b'FL', b'Florida'), (b'GA', b'Georgia'), (b'GU', b'Guam'), (b'HI', b'Hawaii'), (b'ID', b'Idaho'), (b'IL', b'Illinois'), (b'IN', b'Indiana'), (b'IA', b'Iowa'), (b'KS', b'Kansas'), (b'KY', b'Kentucky'), (b'LA', b'Louisiana'), (b'ME', b'Maine'), (b'MD', b'Maryland'), (b'MA', b'Massachusetts'), (b'MI', b'Michigan'), (b'MN', b'Minnesota'), (b'MS', b'Mississippi'), (b'MO', b'Missouri'), (b'MT', b'Montana'), (b'NE', b'Nebraska'), (b'NV', b'Nevada'), (b'NH', b'New Hampshire'), (b'NJ', b'New Jersey'), (b'NM', b'New Mexico'), (b'NY', b'New York'), (b'NC', b'North Carolina'), (b'ND', b'North Dakota'), (b'MP', b'Northern Mariana Islands'), (b'OH', b'Ohio'), (b'OK', b'Oklahoma'), (b'OR', b'Oregon'), (b'PA', b'Pennsylvania'), (b'PR', b'Puerto Rico'), (b'RI', b'Rhode Island'), (b'SC', b'South Carolina'), (b'SD', b'South Dakota'), (b'TN', b'Tennessee'), (b'TX', b'Texas'), (b'UT', b'Utah'), (b'VT', b'Vermont'), (b'VI', b'Virgin Islands'), (b'VA', b'Virginia'), (b'WA', b'Washington'), (b'WV', b'West Virginia'), (b'WI', b'Wisconsin'), (b'WY', b'Wyoming')])),
                ('address_zip', models.CharField(max_length=5, null=True, verbose_name=b'Zip code', blank=True)),
                ('address_postal', models.TextField(null=True, blank=True)),
                ('undeliverable', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'users_contactinfo',
            },
            bases=(models.Model, esp.customforms.linkfields.CustomFormsLinkModel),
        ),
        migrations.CreateModel(
            name='EducatorInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subject_taught', models.CharField(max_length=64, null=True, blank=True)),
                ('grades_taught', models.CharField(max_length=16, null=True, blank=True)),
                ('school', models.CharField(max_length=128, null=True, blank=True)),
                ('position', models.CharField(max_length=64, null=True, blank=True)),
            ],
            options={
                'db_table': 'users_educatorinfo',
            },
        ),
        migrations.CreateModel(
            name='EmailPref',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=64, unique=True, null=True, blank=True)),
                ('email_opt_in', models.BooleanField(default=True)),
                ('first_name', models.CharField(max_length=64)),
                ('last_name', models.CharField(max_length=64)),
                ('sms_number', localflavor.us.models.PhoneNumberField(max_length=20, null=True, blank=True)),
                ('sms_opt_in', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='ESPUser_Profile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'db_table': 'users_espuser_profile',
            },
        ),
        migrations.CreateModel(
            name='GradeChangeRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True)),
                ('claimed_grade', models.PositiveIntegerField()),
                ('grade_before_request', models.PositiveIntegerField()),
                ('reason', models.TextField()),
                ('approved', models.NullBooleanField()),
                ('acknowledged_time', models.DateTimeField(null=True, blank=True)),
            ],
            options={
                'ordering': ['-acknowledged_time', '-created'],
            },
        ),
        migrations.CreateModel(
            name='GuardianInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year_finished', models.PositiveIntegerField(null=True, blank=True)),
                ('num_kids', models.PositiveIntegerField(null=True, blank=True)),
            ],
            options={
                'db_table': 'users_guardianinfo',
            },
        ),
        migrations.CreateModel(
            name='K12School',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('school_type', models.TextField(help_text=b'i.e. Public, Private, Charter, Magnet, ...', null=True, blank=True)),
                ('grades', models.TextField(help_text=b'i.e. "PK, K, 1, 2, 3"', null=True, blank=True)),
                ('school_id', models.CharField(help_text=b'An 8-digit ID number.', max_length=128, null=True, blank=True)),
                ('contact_title', models.TextField(null=True, blank=True)),
                ('name', models.TextField(null=True, blank=True)),
                ('contact', esp.db.fields.AjaxForeignKey(blank=True, to='users.ContactInfo', help_text=b'A set of contact information for this school. Type to search by name (Last, First), or <a href="/admin/users/contactinfo/add/">go edit a new one</a>.', null=True)),
            ],
            options={
                'db_table': 'users_k12school',
            },
        ),
        migrations.CreateModel(
            name='PasswordRecoveryTicket',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('recover_key', models.CharField(max_length=30)),
                ('expire', models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateTimeField(default=datetime.datetime.now, help_text=b'If blank, has always started.', null=True, blank=True)),
                ('end_date', models.DateTimeField(default=None, help_text=b'If blank, never ends.', null=True, blank=True)),
                ('permission_type', models.CharField(max_length=80, choices=[(b'Administer', b'Full administrative permissions'), (b'View', b'Able to view a program'), (b'Onsite', b'Access to onsite interfaces'), (b'GradeOverride', b'Ignore grade ranges for studentreg'), (b'Student Deadlines', ((b'Student', b'Basic student access'), (b'Student/OverrideFull', b'Register for a full program'), (b'Student/All', b'All student deadlines'), (b'Student/Applications', b'Apply for classes'), (b'Student/Catalog', b'View the catalog'), (b'Student/Classes', b'Classes'), (b'Student/Classes/OneClass', b'Classes/OneClass'), (b'Student/Classes/Lottery', b'Enter the lottery'), (b'Student/Classes/Lottery/View', b'View lottery results'), (b'Student/ExtraCosts', b'Extra costs page'), (b'Student/MainPage', b'Registration mainpage'), (b'Student/Confirm', b'Confirm registration'), (b'Student/Cancel', b'Cancel registration'), (b'Student/Payment', b'Pay for a program'), (b'Student/Profile', b'Set profile info'), (b'Student/Survey', b'Access to survey'), (b'Student/FormstackMedliab', b'Access to Formstack medical and liability form'), (b'Student/Finaid', b'Access to financial aid application'))), (b'Teacher Deadlines', ((b'Teacher', b'Basic teacher access'), (b'Teacher/All', b'All teacher deadlines'), (b'Teacher/Acknowledgement', b'Teacher acknowledgement'), (b'Teacher/AppReview', b"Review students' apps"), (b'Teacher/Availability', b'Set availability'), (b'Teacher/Catalog', b'Catalog'), (b'Teacher/Classes', b'Classes'), (b'Teacher/Classes/All', b'Classes/All'), (b'Teacher/Classes/View', b'Classes/View'), (b'Teacher/Classes/Edit', b'Classes/Edit'), (b'Teacher/Classes/Create', b'Create classes of all types'), (b'Teacher/Classes/Create/Class', b'Create standard classes'), (b'Teacher/Classes/Create/OpenClass', b'Create open classes'), (b'Teacher/Classes/SelectStudents', b'Classes/SelectStudents'), (b'Teacher/Events', b'Teacher training signup'), (b'Teacher/Quiz', b'Teacher quiz'), (b'Teacher/MainPage', b'Registration mainpage'), (b'Teacher/Survey', b'Teacher Survey'), (b'Teacher/Profile', b'Set profile info'), (b'Teacher/Survey', b'Access to survey')))])),
                ('program', models.ForeignKey(blank=True, to='program.Program', null=True)),
                ('role', models.ForeignKey(blank=True, to='auth.Group', help_text=b'Apply this permission to an entire user role (can be blank).', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PersistentQueryFilter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('item_model', models.CharField(max_length=256)),
                ('q_filter', models.TextField()),
                ('sha1_hash', models.CharField(max_length=256)),
                ('create_ts', models.DateTimeField(auto_now_add=True)),
                ('useful_name', models.CharField(max_length=1024, null=True, blank=True)),
            ],
            options={
                'db_table': 'users_persistentqueryfilter',
            },
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('event', models.CharField(max_length=80, choices=[(b'student_survey', b'Completed student survey'), (b'teacher_survey', b'Completed teacher survey'), (b'reg_confirmed', b'Confirmed registration'), (b'attended', b'Attended program'), (b'conf_email', b'Was sent confirmation email'), (b'teacher_quiz_done', b'Completed teacher quiz'), (b'paid', b'Paid for program'), (b'med', b'Submitted medical form'), (b'med_bypass', b'Recieved medical bypass'), (b'liab', b'Submitted liability form'), (b'onsite', b'Registered for program onsite'), (b'schedule_printed', b'Printed student schedule onsite'), (b'teacheracknowledgement', b'Did teacher acknowledgement'), (b'lunch_selected', b'Selected a lunch block'), (b'extra_form_done', b'Filled out Custom Form'), (b'extra_costs_done', b'Filled out Student Extra Costs Form'), (b'donation_done', b'Filled out Donation Form'), (b'waitlist', b'Waitlisted for a program'), (b'interview', b'Teacher-interviewed for a program'), (b'teacher_training', b'Attended teacher-training for a program'), (b'teacher_checked_in', b'Teacher checked in for teaching on the day of the program'), (b'twophase_reg_done', b'Completed two-phase registration')])),
                ('time', models.DateTimeField(default=datetime.datetime.now, blank=True)),
                ('program', models.ForeignKey(blank=True, to='program.Program', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='StudentInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('graduation_year', models.PositiveIntegerField(null=True, blank=True)),
                ('school', models.CharField(max_length=256, null=True, blank=True)),
                ('dob', models.DateField(null=True, blank=True)),
                ('gender', models.CharField(max_length=32, null=True, blank=True)),
                ('studentrep', models.BooleanField(default=False)),
                ('studentrep_expl', models.TextField(null=True, blank=True)),
                ('heard_about', models.TextField(null=True, blank=True)),
                ('food_preference', models.CharField(max_length=256, null=True, blank=True)),
                ('shirt_size', models.CharField(blank=True, max_length=5, null=True, choices=[(b'14/16', b'14/16 (XS)'), (b'S', b'S'), (b'M', b'M'), (b'L', b'L'), (b'XL', b'XL'), (b'XXL', b'XXL')])),
                ('shirt_type', models.CharField(blank=True, max_length=20, null=True, choices=[(b'M', b'Plain'), (b'F', b'Fitted (for women)')])),
                ('medical_needs', models.TextField(null=True, blank=True)),
                ('schoolsystem_id', models.CharField(max_length=32, null=True, blank=True)),
                ('schoolsystem_optout', models.BooleanField(default=False)),
                ('post_hs', models.TextField(default=b'', blank=True)),
                ('transportation', models.TextField(default=b'', blank=True)),
                ('k12school', esp.db.fields.AjaxForeignKey(blank=True, to='users.K12School', help_text=b'Begin to type your school name and select your school if it comes up.', null=True)),
            ],
            options={
                'db_table': 'users_studentinfo',
            },
        ),
        migrations.CreateModel(
            name='TeacherInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('graduation_year', models.CharField(max_length=4, null=True, blank=True)),
                ('from_here', models.NullBooleanField()),
                ('is_graduate_student', models.NullBooleanField()),
                ('college', models.CharField(max_length=128, null=True, blank=True)),
                ('major', models.CharField(max_length=32, null=True, blank=True)),
                ('bio', models.TextField(null=True, blank=True)),
                ('shirt_size', models.CharField(blank=True, max_length=5, null=True, choices=[(b'14/16', b'14/16 (XS)'), (b'S', b'S'), (b'M', b'M'), (b'L', b'L'), (b'XL', b'XL'), (b'XXL', b'XXL')])),
                ('shirt_type', models.CharField(blank=True, max_length=20, null=True, choices=[(b'M', b'Plain'), (b'F', b'Fitted (for women)')])),
                ('full_legal_name', models.CharField(max_length=128, null=True, blank=True)),
                ('university_email', models.EmailField(max_length=75, null=True, blank=True)),
                ('student_id', models.CharField(max_length=128, null=True, blank=True)),
                ('mail_reimbursement', models.NullBooleanField()),
            ],
            bases=(models.Model, esp.customforms.linkfields.CustomFormsLinkModel),
        ),
        migrations.CreateModel(
            name='UserAvailability',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('priority', models.DecimalField(default=b'1.0', max_digits=3, decimal_places=2)),
                ('event', models.ForeignKey(to='cal.Event')),
                ('role', models.ForeignKey(to='auth.Group')),
            ],
            options={
                'db_table': 'users_useravailability',
            },
        ),
        migrations.CreateModel(
            name='UserForwarder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='ZipCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('zip_code', models.CharField(max_length=5)),
                ('latitude', models.DecimalField(max_digits=10, decimal_places=6)),
                ('longitude', models.DecimalField(max_digits=10, decimal_places=6)),
            ],
            options={
                'db_table': 'users_zipcode',
            },
        ),
        migrations.CreateModel(
            name='ZipCodeSearches',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('distance', models.DecimalField(max_digits=15, decimal_places=3)),
                ('zipcodes', models.TextField()),
                ('zip_code', models.ForeignKey(to='users.ZipCode')),
            ],
            options={
                'db_table': 'users_zipcodesearches',
            },
        ),
        migrations.CreateModel(
            name='ESPUser',
            fields=[
            ],
            options={
                'verbose_name': 'ESP User',
                'proxy': True,
            },
            bases=('auth.user', django.contrib.auth.models.AnonymousUser),
        ),
        migrations.AddField(
            model_name='userforwarder',
            name='source',
            field=esp.db.fields.AjaxForeignKey(related_name='forwarders_out', to='users.ESPUser', unique=True),
        ),
        migrations.AddField(
            model_name='userforwarder',
            name='target',
            field=esp.db.fields.AjaxForeignKey(related_name='forwarders_in', to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='useravailability',
            name='user',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='teacherinfo',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='studentinfo',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True),
        ),
        migrations.AddField(
            model_name='record',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True),
        ),
        migrations.AddField(
            model_name='permission',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', help_text=b'Blank does NOT mean apply to everyone, use role-based permissions for that.', null=True),
        ),
        migrations.AddField(
            model_name='passwordrecoveryticket',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='guardianinfo',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True),
        ),
        migrations.AddField(
            model_name='gradechangerequest',
            name='acknowledged_by',
            field=models.ForeignKey(blank=True, to='users.ESPUser', null=True),
        ),
        migrations.AddField(
            model_name='gradechangerequest',
            name='requesting_student',
            field=models.ForeignKey(related_name='requesting_student_set', to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='espuser_profile',
            name='user',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser', unique=True),
        ),
        migrations.AddField(
            model_name='educatorinfo',
            name='k12school',
            field=models.ForeignKey(blank=True, to='users.K12School', null=True),
        ),
        migrations.AddField(
            model_name='educatorinfo',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True),
        ),
        migrations.AddField(
            model_name='contactinfo',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
