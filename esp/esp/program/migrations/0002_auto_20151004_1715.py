# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cal', '0002_event_program'),
        ('program', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='volunteeroffer',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True),
        ),
        migrations.AddField(
            model_name='teacherbio',
            name='program',
            field=models.ForeignKey(blank=True, to='program.Program', null=True),
        ),
        migrations.AddField(
            model_name='teacherbio',
            name='user',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='studentsubjectinterest',
            name='subject',
            field=esp.db.fields.AjaxForeignKey(to='program.ClassSubject'),
        ),
        migrations.AddField(
            model_name='studentsubjectinterest',
            name='user',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='studentregistration',
            name='relationship',
            field=models.ForeignKey(to='program.RegistrationType'),
        ),
        migrations.AddField(
            model_name='studentregistration',
            name='section',
            field=esp.db.fields.AjaxForeignKey(to='program.ClassSection'),
        ),
        migrations.AddField(
            model_name='studentregistration',
            name='user',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='studentappreview',
            name='reviewer',
            field=esp.db.fields.AjaxForeignKey(editable=False, to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='studentappresponse',
            name='question',
            field=models.ForeignKey(editable=False, to='program.StudentAppQuestion'),
        ),
        migrations.AddField(
            model_name='studentappquestion',
            name='program',
            field=models.ForeignKey(blank=True, editable=False, to='program.Program', null=True),
        ),
        migrations.AddField(
            model_name='studentappquestion',
            name='subject',
            field=models.ForeignKey(blank=True, editable=False, to='program.ClassSubject', null=True),
        ),
        migrations.AddField(
            model_name='studentapplication',
            name='program',
            field=models.ForeignKey(editable=False, to='program.Program'),
        ),
        migrations.AddField(
            model_name='studentapplication',
            name='questions',
            field=models.ManyToManyField(to='program.StudentAppQuestion'),
        ),
        migrations.AddField(
            model_name='studentapplication',
            name='responses',
            field=models.ManyToManyField(to='program.StudentAppResponse'),
        ),
        migrations.AddField(
            model_name='studentapplication',
            name='reviews',
            field=models.ManyToManyField(to='program.StudentAppReview'),
        ),
        migrations.AddField(
            model_name='studentapplication',
            name='user',
            field=esp.db.fields.AjaxForeignKey(editable=False, to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='splashinfo',
            name='program',
            field=esp.db.fields.AjaxForeignKey(to='program.Program', null=True),
        ),
        migrations.AddField(
            model_name='splashinfo',
            name='student',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='scheduleconstraint',
            name='condition',
            field=models.ForeignKey(related_name='condition_constraint', to='program.BooleanExpression'),
        ),
        migrations.AddField(
            model_name='scheduleconstraint',
            name='program',
            field=models.ForeignKey(to='program.Program'),
        ),
        migrations.AddField(
            model_name='scheduleconstraint',
            name='requirement',
            field=models.ForeignKey(related_name='requirement_constraint', to='program.BooleanExpression'),
        ),
        migrations.AlterUniqueTogether(
            name='registrationtype',
            unique_together=set([('name', 'category')]),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='contact_emergency',
            field=esp.db.fields.AjaxForeignKey(related_name='as_emergency', blank=True, to='users.ContactInfo', null=True),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='contact_guardian',
            field=esp.db.fields.AjaxForeignKey(related_name='as_guardian', blank=True, to='users.ContactInfo', null=True),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='contact_user',
            field=esp.db.fields.AjaxForeignKey(related_name='as_user', blank=True, to='users.ContactInfo', null=True),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='educator_info',
            field=esp.db.fields.AjaxForeignKey(related_name='as_educator', blank=True, to='users.EducatorInfo', null=True),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='guardian_info',
            field=esp.db.fields.AjaxForeignKey(related_name='as_guardian', blank=True, to='users.GuardianInfo', null=True),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='program',
            field=models.ForeignKey(blank=True, to='program.Program', null=True),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='student_info',
            field=esp.db.fields.AjaxForeignKey(related_name='as_student', blank=True, to='users.StudentInfo', null=True),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='teacher_info',
            field=esp.db.fields.AjaxForeignKey(related_name='as_teacher', blank=True, to='users.TeacherInfo', null=True),
        ),
        migrations.AddField(
            model_name='registrationprofile',
            name='user',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='programcheckitem',
            name='program',
            field=models.ForeignKey(related_name='checkitems', to='program.Program'),
        ),
        migrations.AddField(
            model_name='program',
            name='class_categories',
            field=models.ManyToManyField(to='program.ClassCategories'),
        ),
        migrations.AddField(
            model_name='program',
            name='flag_types',
            field=models.ManyToManyField(help_text='The set of flags that can be used to tag classes for this program. Add flag types in <a href="/admin/program/classflagtype/">the admin panel</a>.', to='program.ClassFlagType', blank=True),
        ),
        migrations.AddField(
            model_name='program',
            name='program_modules',
            field=models.ManyToManyField(help_text=b'The set of enabled program functionalities. See <a href="https://github.com/learning-unlimited/ESP-Website/blob/main/docs/admin/program_modules.rst">the documentation</a> for details.', to='program.ProgramModule'),
        ),
        migrations.AddField(
            model_name='financialaidrequest',
            name='program',
            field=models.ForeignKey(editable=False, to='program.Program'),
        ),
        migrations.AddField(
            model_name='financialaidrequest',
            name='user',
            field=esp.db.fields.AjaxForeignKey(editable=False, to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='allowable_class_size_ranges',
            field=models.ManyToManyField(related_name='classsubject_allowedsizes', null=True, to='program.ClassSizeRange', blank=True),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='category',
            field=models.ForeignKey(related_name='cls', to='program.ClassCategories'),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='checklist_progress',
            field=models.ManyToManyField(to='program.ProgramCheckItem', blank=True),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='meeting_times',
            field=models.ManyToManyField(to='cal.Event', blank=True),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='optimal_class_size_range',
            field=models.ForeignKey(blank=True, to='program.ClassSizeRange', null=True),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='parent_program',
            field=models.ForeignKey(to='program.Program'),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='teachers',
            field=models.ManyToManyField(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='classsizerange',
            name='program',
            field=models.ForeignKey(blank=True, to='program.Program', null=True),
        ),
        migrations.AddField(
            model_name='classsection',
            name='checklist_progress',
            field=models.ManyToManyField(to='program.ProgramCheckItem', blank=True),
        ),
        migrations.AddField(
            model_name='classsection',
            name='meeting_times',
            field=models.ManyToManyField(related_name='meeting_times', to='cal.Event', blank=True),
        ),
        migrations.AddField(
            model_name='classsection',
            name='parent_class',
            field=esp.db.fields.AjaxForeignKey(related_name='sections', to='program.ClassSubject'),
        ),
        migrations.AddField(
            model_name='classsection',
            name='registrations',
            field=models.ManyToManyField(to='users.ESPUser', through='program.StudentRegistration'),
        ),
        migrations.AddField(
            model_name='classimplication',
            name='cls',
            field=models.ForeignKey(to='program.ClassSubject', null=True),
        ),
        migrations.AddField(
            model_name='classimplication',
            name='parent',
            field=models.ForeignKey(default=None, to='program.ClassImplication', null=True),
        ),
        migrations.AddField(
            model_name='classflag',
            name='created_by',
            field=esp.db.fields.AjaxForeignKey(related_name='classflags_created', to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='classflag',
            name='flag_type',
            field=models.ForeignKey(to='program.ClassFlagType'),
        ),
        migrations.AddField(
            model_name='classflag',
            name='modified_by',
            field=esp.db.fields.AjaxForeignKey(related_name='classflags_modified', to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='classflag',
            name='subject',
            field=esp.db.fields.AjaxForeignKey(related_name='flags', to='program.ClassSubject'),
        ),
        migrations.AddField(
            model_name='booleantoken',
            name='exp',
            field=models.ForeignKey(help_text=b'The Boolean expression that this token belongs to', to='program.BooleanExpression'),
        ),
        migrations.CreateModel(
            name='ScheduleTestCategory',
            fields=[
                ('scheduletesttimeblock_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='program.ScheduleTestTimeblock')),
                ('category', models.ForeignKey(help_text=b'The class category that must be selected for this timeblock', to='program.ClassCategories')),
            ],
            bases=('program.scheduletesttimeblock',),
        ),
        migrations.CreateModel(
            name='ScheduleTestOccupied',
            fields=[
                ('scheduletesttimeblock_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='program.ScheduleTestTimeblock')),
            ],
            bases=('program.scheduletesttimeblock',),
        ),
        migrations.CreateModel(
            name='ScheduleTestSectionList',
            fields=[
                ('scheduletesttimeblock_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='program.ScheduleTestTimeblock')),
                ('section_ids', models.TextField(help_text=b'A comma separated list of ClassSection IDs that can be selected for this timeblock')),
            ],
            bases=('program.scheduletesttimeblock',),
        ),
        migrations.AddField(
            model_name='scheduletesttimeblock',
            name='timeblock',
            field=models.ForeignKey(help_text=b'The timeblock that this schedule test pertains to', to='cal.Event'),
        ),
        migrations.AlterUniqueTogether(
            name='financialaidrequest',
            unique_together=set([('program', 'user')]),
        ),
    ]
