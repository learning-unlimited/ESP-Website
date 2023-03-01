# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
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
                ('e_mail', models.EmailField(max_length=75, null=True, verbose_name='Email address', blank=True)),
                ('phone_day', localflavor.us.models.PhoneNumberField(max_length=20, null=True, verbose_name='Home phone', blank=True)),
                ('phone_cell', localflavor.us.models.PhoneNumberField(max_length=20, null=True, verbose_name='Cell phone', blank=True)),
                ('receive_txt_message', models.BooleanField(default=False)),
                ('phone_even', localflavor.us.models.PhoneNumberField(max_length=20, null=True, verbose_name='Alternate phone', blank=True)),
                ('address_street', models.CharField(max_length=100, null=True, verbose_name='Street address', blank=True)),
                ('address_city', models.CharField(max_length=50, null=True, verbose_name='City', blank=True)),
                ('address_state', localflavor.us.models.USStateField(blank=True, max_length=2, null=True, verbose_name='State', choices=[('AL', 'Alabama'), ('AK', 'Alaska'), ('AS', 'American Samoa'), ('AZ', 'Arizona'), ('AR', 'Arkansas'), ('AA', 'Armed Forces Americas'), ('AE', 'Armed Forces Europe'), ('AP', 'Armed Forces Pacific'), ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'), ('DC', 'District of Columbia'), ('FL', 'Florida'), ('GA', 'Georgia'), ('GU', 'Guam'), ('HI', 'Hawaii'), ('ID', 'Idaho'), ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'), ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'), ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('MP', 'Northern Mariana Islands'), ('OH', 'Ohio'), ('OK', 'Oklahoma'), ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('PR', 'Puerto Rico'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'), ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'), ('VT', 'Vermont'), ('VI', 'Virgin Islands'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming')])),
                ('address_zip', models.CharField(max_length=5, null=True, verbose_name='Zip code', blank=True)),
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
                ('school_type', models.TextField(help_text='i.e. Public, Private, Charter, Magnet, ...', null=True, blank=True)),
                ('grades', models.TextField(help_text='i.e. "PK, K, 1, 2, 3"', null=True, blank=True)),
                ('school_id', models.CharField(help_text='An 8-digit ID number.', max_length=128, null=True, blank=True)),
                ('contact_title', models.TextField(null=True, blank=True)),
                ('name', models.TextField(null=True, blank=True)),
                ('contact', esp.db.fields.AjaxForeignKey(blank=True, to='users.ContactInfo', help_text='A set of contact information for this school. Type to search by name (Last, First), or <a href="/admin/users/contactinfo/add/">go edit a new one</a>.', null=True)),
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
                ('start_date', models.DateTimeField(default=datetime.datetime.now, help_text='If blank, has always started.', null=True, blank=True)),
                ('end_date', models.DateTimeField(default=None, help_text='If blank, never ends.', null=True, blank=True)),
                ('permission_type', models.CharField(max_length=80, choices=[('Administer', 'Full administrative permissions'), ('View', 'Able to view a program'), ('Onsite', 'Access to onsite interfaces'), ('GradeOverride', 'Ignore grade ranges for studentreg'), ('Student Deadlines', (('Student', 'Basic student access'), ('Student/OverrideFull', 'Register for a full program'), ('Student/All', 'All student deadlines'), ('Student/Applications', 'Apply for classes'), ('Student/Catalog', 'View the catalog'), ('Student/Classes', 'Classes'), ('Student/Classes/OneClass', 'Classes/OneClass'), ('Student/Classes/Lottery', 'Enter the lottery'), ('Student/Classes/Lottery/View', 'View lottery results'), ('Student/ExtraCosts', 'Extra costs page'), ('Student/MainPage', 'Registration mainpage'), ('Student/Confirm', 'Confirm registration'), ('Student/Cancel', 'Cancel registration'), ('Student/Payment', 'Pay for a program'), ('Student/Profile', 'Set profile info'), ('Student/Survey', 'Access to survey'), ('Student/FormstackMedliab', 'Access to Formstack medical and liability form'), ('Student/Finaid', 'Access to financial aid application'))), ('Teacher Deadlines', (('Teacher', 'Basic teacher access'), ('Teacher/All', 'All teacher deadlines'), ('Teacher/Acknowledgement', 'Teacher acknowledgement'), ('Teacher/AppReview', "Review students' apps"), ('Teacher/Availability', 'Set availability'), ('Teacher/Catalog', 'Catalog'), ('Teacher/Classes', 'Classes'), ('Teacher/Classes/All', 'Classes/All'), ('Teacher/Classes/View', 'Classes/View'), ('Teacher/Classes/Edit', 'Classes/Edit'), ('Teacher/Classes/Create', 'Create classes of all types'), ('Teacher/Classes/Create/Class', 'Create standard classes'), ('Teacher/Classes/Create/OpenClass', 'Create open classes'), ('Teacher/Classes/SelectStudents', 'Classes/SelectStudents'), ('Teacher/Events', 'Teacher training signup'), ('Teacher/Quiz', 'Teacher quiz'), ('Teacher/MainPage', 'Registration mainpage'), ('Teacher/Survey', 'Teacher Survey'), ('Teacher/Profile', 'Set profile info'), ('Teacher/Survey', 'Access to survey')))])),
                ('program', models.ForeignKey(blank=True, to='program.Program', null=True)),
                ('role', models.ForeignKey(blank=True, to='auth.Group', help_text='Apply this permission to an entire user role (can be blank).', null=True)),
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
                ('event', models.CharField(max_length=80, choices=[('student_survey', 'Completed student survey'), ('teacher_survey', 'Completed teacher survey'), ('reg_confirmed', 'Confirmed registration'), ('attended', 'Attended program'), ('conf_email', 'Was sent confirmation email'), ('teacher_quiz_done', 'Completed teacher quiz'), ('paid', 'Paid for program'), ('med', 'Submitted medical form'), ('med_bypass', 'Recieved medical bypass'), ('liab', 'Submitted liability form'), ('onsite', 'Registered for program onsite'), ('schedule_printed', 'Printed student schedule onsite'), ('teacheracknowledgement', 'Did teacher acknowledgement'), ('lunch_selected', 'Selected a lunch block'), ('extra_form_done', 'Filled out Custom Form'), ('extra_costs_done', 'Filled out Student Extra Costs Form'), ('donation_done', 'Filled out Donation Form'), ('waitlist', 'Waitlisted for a program'), ('interview', 'Teacher-interviewed for a program'), ('teacher_training', 'Attended teacher-training for a program'), ('teacher_checked_in', 'Teacher checked in for teaching on the day of the program'), ('twophase_reg_done', 'Completed two-phase registration')])),
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
                ('shirt_size', models.CharField(blank=True, max_length=5, null=True, choices=[('14/16', '14/16 (XS)'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL')])),
                ('shirt_type', models.CharField(blank=True, max_length=20, null=True, choices=[('M', 'Plain'), ('F', 'Fitted (for women)')])),
                ('medical_needs', models.TextField(null=True, blank=True)),
                ('schoolsystem_id', models.CharField(max_length=32, null=True, blank=True)),
                ('schoolsystem_optout', models.BooleanField(default=False)),
                ('post_hs', models.TextField(default='', blank=True)),
                ('transportation', models.TextField(default='', blank=True)),
                ('k12school', esp.db.fields.AjaxForeignKey(blank=True, to='users.K12School', help_text='Begin to type your school name and select your school if it comes up.', null=True)),
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
                ('shirt_size', models.CharField(blank=True, max_length=5, null=True, choices=[('14/16', '14/16 (XS)'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL')])),
                ('shirt_type', models.CharField(blank=True, max_length=20, null=True, choices=[('M', 'Plain'), ('F', 'Fitted (for women)')])),
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
                ('priority', models.DecimalField(default='1.0', max_digits=3, decimal_places=2)),
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
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', help_text='Blank does NOT mean apply to everyone, use role-based permissions for that.', null=True),
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
