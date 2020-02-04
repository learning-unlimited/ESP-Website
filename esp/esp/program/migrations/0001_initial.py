# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import localflavor.us.models
import datetime
import esp.customforms.linkfields
import django.utils.timezone
import esp.utils.fields
import esp.program.models.app_


class Migration(migrations.Migration):

    dependencies = [
        ('cal', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchiveClass',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('program', models.CharField(max_length=256)),
                ('year', models.CharField(max_length=4)),
                ('date', models.CharField(max_length=128)),
                ('category', models.CharField(max_length=32)),
                ('teacher', models.CharField(max_length=1024)),
                ('title', models.CharField(max_length=1024)),
                ('description', models.TextField()),
                ('teacher_ids', models.CharField(max_length=256, null=True, blank=True)),
                ('student_ids', models.TextField()),
                ('original_id', models.IntegerField(null=True, blank=True)),
                ('num_old_students', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'program_archiveclass',
                'verbose_name_plural': 'archive classes',
            },
        ),
        migrations.CreateModel(
            name='BooleanExpression',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(help_text=b'Description of the expression', max_length=80)),
            ],
        ),
        migrations.CreateModel(
            name='BooleanToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.TextField(default=b'', help_text=b'Boolean value, or text needed to compute it', blank=True)),
                ('seq', models.IntegerField(default=0, help_text=b'Location of this token on the expression stack (larger numbers are higher)')),
            ],
        ),
        migrations.CreateModel(
            name='ClassCategories',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.TextField()),
                ('symbol', models.CharField(default=b'?', max_length=1)),
                ('seq', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'program_classcategories',
                'verbose_name_plural': 'Class Categories',
            },
        ),
        migrations.CreateModel(
            name='ClassFlag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('comment', models.TextField(blank=True)),
                ('modified_time', models.DateTimeField(auto_now=True)),
                ('created_time', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['flag_type'],
            },
        ),
        migrations.CreateModel(
            name='ClassFlagType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('show_in_scheduler', models.BooleanField(default=False)),
                ('show_in_dashboard', models.BooleanField(default=False)),
                ('seq', models.SmallIntegerField(default=0, help_text=b'Flag types will be ordered by this.  Smaller is earlier; the default is 0.')),
                ('color', models.CharField(help_text=b'A color for displaying this flag type.  Should be a valid CSS color, for example "red", "#ff0000", or "rgb(255, 0, 0)".  If blank, an arbitrary one will be chosen.', max_length=20, blank=True)),
            ],
            options={
                'ordering': ['seq'],
            },
        ),
        migrations.CreateModel(
            name='ClassImplication',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_prereq', models.BooleanField(default=True)),
                ('enforce', models.BooleanField(default=True)),
                ('member_ids', models.CommaSeparatedIntegerField(max_length=100, blank=True)),
                ('operation', models.CharField(max_length=4, choices=[(b'AND', b'All'), (b'OR', b'Any'), (b'XOR', b'Exactly One')])),
            ],
            options={
                'db_table': 'program_classimplications',
                'verbose_name_plural': 'Class Implications',
            },
        ),
        migrations.CreateModel(
            name='ClassSection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.IntegerField(default=0, choices=[(-20, b'cancelled'), (-10, b'rejected'), (0, b'unreviewed'), (5, b'accepted but hidden'), (10, b'accepted')])),
                ('registration_status', models.IntegerField(default=0, choices=[(0, b'open'), (10, b'closed')])),
                ('duration', models.DecimalField(null=True, max_digits=5, decimal_places=2, blank=True)),
                ('max_class_capacity', models.IntegerField(null=True, blank=True)),
                ('enrolled_students', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['id'],
                'db_table': 'program_classsection',
            },
        ),
        migrations.CreateModel(
            name='ClassSizeRange',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('range_min', models.IntegerField()),
                ('range_max', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='ClassSubject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.TextField()),
                ('class_info', models.TextField(blank=True)),
                ('allow_lateness', models.BooleanField(default=False)),
                ('message_for_directors', models.TextField(blank=True)),
                ('class_size_optimal', models.IntegerField(null=True, blank=True)),
                ('grade_min', models.IntegerField()),
                ('grade_max', models.IntegerField()),
                ('class_size_min', models.IntegerField(null=True, blank=True)),
                ('hardness_rating', models.TextField(null=True, blank=True)),
                ('class_size_max', models.IntegerField(null=True, blank=True)),
                ('schedule', models.TextField(blank=True)),
                ('prereqs', models.TextField(null=True, blank=True)),
                ('requested_special_resources', models.TextField(null=True, blank=True)),
                ('directors_notes', models.TextField(null=True, blank=True)),
                ('requested_room', models.TextField(null=True, blank=True)),
                ('session_count', models.IntegerField(default=1)),
                ('purchase_requests', models.TextField(null=True, blank=True)),
                ('custom_form_data', esp.utils.fields.JSONField(null=True, blank=True)),
                ('status', models.IntegerField(default=0, choices=[(-20, b'cancelled'), (-10, b'rejected'), (0, b'unreviewed'), (5, b'accepted but hidden'), (10, b'accepted')])),
                ('duration', models.DecimalField(null=True, max_digits=5, decimal_places=2, blank=True)),
            ],
            options={
                'db_table': 'program_class',
            },
            bases=(models.Model, esp.customforms.linkfields.CustomFormsLinkModel),
        ),
        migrations.CreateModel(
            name='FinancialAidRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('reduced_lunch', models.BooleanField(default=False, verbose_name=b'Do you receive free/reduced lunch at school?')),
                ('household_income', models.CharField(max_length=12, null=True, verbose_name=b'Approximately what is your household income (round to the nearest $10,000)?', blank=True)),
                ('extra_explaination', models.TextField(null=True, verbose_name=b'Please describe in detail your financial situation this year', blank=True)),
                ('student_prepare', models.BooleanField(default=False, verbose_name=b'Did anyone besides the student fill out any portions of this form?')),
                ('done', models.BooleanField(default=False, editable=False)),
            ],
            options={
                'db_table': 'program_financialaidrequest',
            },
        ),
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(max_length=80)),
                ('name', models.CharField(max_length=80)),
                ('grade_min', models.IntegerField()),
                ('grade_max', models.IntegerField()),
                ('director_email', models.EmailField(max_length=75)),
                ('director_cc_email', models.EmailField(default=b'', help_text=b'If set, automated outgoing mail (except class cancellations) will be sent to this address instead of the director email. Use this if you do not want to spam the director email with teacher class registration emails. Otherwise, leave this field blank.', max_length=75, blank=True)),
                ('director_confidential_email', models.EmailField(default=b'', help_text=b'If set, confidential emails such as financial aid applications will be sent to this address instead of the director email.', max_length=75, blank=True)),
                ('program_size_max', models.IntegerField(null=True)),
                ('program_allow_waitlist', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'program_program',
            },
            bases=(models.Model, esp.customforms.linkfields.CustomFormsLinkModel),
        ),
        migrations.CreateModel(
            name='ProgramCheckItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=512)),
                ('seq', models.PositiveIntegerField(help_text=b'Lower is earlier', verbose_name=b'Sequence', blank=True)),
            ],
            options={
                'ordering': ('seq',),
                'db_table': 'program_programcheckitem',
            },
        ),
        migrations.CreateModel(
            name='ProgramModule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('link_title', models.CharField(max_length=64, null=True, blank=True)),
                ('admin_title', models.CharField(max_length=128)),
                ('inline_template', models.CharField(max_length=32, null=True, blank=True)),
                ('module_type', models.CharField(max_length=32)),
                ('handler', models.CharField(max_length=32)),
                ('seq', models.IntegerField()),
                ('required', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'program_programmodule',
            },
        ),
        migrations.CreateModel(
            name='RegistrationProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_ts', models.DateTimeField(default=django.utils.timezone.now)),
                ('emailverifycode', models.TextField(null=True, blank=True)),
                ('email_verified', models.BooleanField(default=False)),
                ('most_recent_profile', models.BooleanField(default=False)),
                ('old_text_reminder', models.NullBooleanField(db_column=b'text_reminder')),
            ],
            options={
                'db_table': 'program_registrationprofile',
            },
        ),
        migrations.CreateModel(
            name='RegistrationType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=32)),
                ('displayName', models.CharField(max_length=32, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('category', models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='ScheduleConstraint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('on_failure', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='SplashInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('lunchsat', models.CharField(max_length=32, null=True, blank=True)),
                ('lunchsun', models.CharField(max_length=32, null=True, blank=True)),
                ('siblingdiscount', models.NullBooleanField(default=False)),
                ('siblingname', models.CharField(max_length=64, null=True, blank=True)),
                ('submitted', models.NullBooleanField(default=False)),
            ],
            options={
                'db_table': 'program_splashinfo',
            },
        ),
        migrations.CreateModel(
            name='StudentApplication',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('done', models.BooleanField(default=False, editable=False)),
                ('teacher_score', models.PositiveIntegerField(null=True, editable=False, blank=True)),
                ('director_score', models.PositiveIntegerField(null=True, editable=False, blank=True)),
                ('rejected', models.BooleanField(default=False, editable=False)),
            ],
            options={
                'db_table': 'program_junctionstudentapp',
            },
        ),
        migrations.CreateModel(
            name='StudentAppQuestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('question', models.TextField(help_text=b'The prompt that your students will see.')),
                ('directions', models.TextField(help_text=b'Specify any additional notes (such as the length of response you desire) here.', null=True, blank=True)),
            ],
            options={
                'db_table': 'program_studentappquestion',
            },
            bases=(esp.program.models.app_.BaseAppElement, models.Model),
        ),
        migrations.CreateModel(
            name='StudentAppResponse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('response', models.TextField(default=b'')),
                ('complete', models.BooleanField(default=False, help_text=b'Please check this box when you are finished responding to this question.')),
            ],
            options={
                'db_table': 'program_studentappresponse',
            },
            bases=(esp.program.models.app_.BaseAppElement, models.Model),
        ),
        migrations.CreateModel(
            name='StudentAppReview',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(default=datetime.datetime.now, editable=False)),
                ('score', models.PositiveIntegerField(blank=True, help_text=b'Please rate each student', null=True, choices=[(10, b'Yes'), (5, b'Maybe'), (1, b'No')])),
                ('comments', models.TextField()),
                ('reject', models.BooleanField(default=False, editable=False)),
            ],
            options={
                'db_table': 'program_studentappreview',
            },
            bases=(esp.program.models.app_.BaseAppElement, models.Model),
        ),
        migrations.CreateModel(
            name='StudentRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateTimeField(default=datetime.datetime.now, help_text=b'If blank, has always started.', null=True, blank=True)),
                ('end_date', models.DateTimeField(default=None, help_text=b'If blank, never ends.', null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='StudentSubjectInterest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateTimeField(default=datetime.datetime.now, help_text=b'If blank, has always started.', null=True, blank=True)),
                ('end_date', models.DateTimeField(default=None, help_text=b'If blank, never ends.', null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='TeacherBio',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('bio', models.TextField(null=True, blank=True)),
                ('slugbio', models.CharField(max_length=50, null=True, blank=True)),
                ('picture', models.ImageField(height_field=b'picture_height', width_field=b'picture_width', null=True, upload_to=b'uploaded/bio_pictures/%y_%m/', blank=True)),
                ('picture_height', models.IntegerField(null=True, blank=True)),
                ('picture_width', models.IntegerField(null=True, blank=True)),
                ('last_ts', models.DateTimeField(auto_now=True)),
                ('hidden', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'program_teacherbio',
            },
        ),
        migrations.CreateModel(
            name='VolunteerOffer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('confirmed', models.BooleanField(default=False)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('name', models.CharField(max_length=80, null=True, blank=True)),
                ('phone', localflavor.us.models.PhoneNumberField(max_length=20, null=True, blank=True)),
                ('shirt_size', models.CharField(blank=True, max_length=5, null=True, choices=[(b'14/16', b'14/16 (XS)'), (b'S', b'S'), (b'M', b'M'), (b'L', b'L'), (b'XL', b'XL'), (b'XXL', b'XXL')])),
                ('shirt_type', models.CharField(blank=True, max_length=20, null=True, choices=[(b'M', b'Plain'), (b'F', b'Fitted (for women)')])),
                ('comments', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='VolunteerRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('num_volunteers', models.PositiveIntegerField()),
                ('program', models.ForeignKey(to='program.Program')),
                ('timeslot', models.ForeignKey(to='cal.Event')),
            ],
        ),
        migrations.CreateModel(
            name='ScheduleTestTimeblock',
            fields=[
                ('booleantoken_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='program.BooleanToken')),
            ],
            bases=('program.booleantoken',),
        ),
        migrations.AddField(
            model_name='volunteeroffer',
            name='request',
            field=models.ForeignKey(to='program.VolunteerRequest'),
        ),
    ]
