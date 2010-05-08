
from south.db import db
from django.db import models
from esp.program.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'ArchiveClass'
        db.create_table('program_archiveclass', (
            ('id', orm['program.ArchiveClass:id']),
            ('program', orm['program.ArchiveClass:program']),
            ('year', orm['program.ArchiveClass:year']),
            ('date', orm['program.ArchiveClass:date']),
            ('category', orm['program.ArchiveClass:category']),
            ('teacher', orm['program.ArchiveClass:teacher']),
            ('title', orm['program.ArchiveClass:title']),
            ('description', orm['program.ArchiveClass:description']),
            ('teacher_ids', orm['program.ArchiveClass:teacher_ids']),
            ('student_ids', orm['program.ArchiveClass:student_ids']),
            ('original_id', orm['program.ArchiveClass:original_id']),
            ('num_old_students', orm['program.ArchiveClass:num_old_students']),
        ))
        db.send_create_signal('program', ['ArchiveClass'])
        
        # Adding model 'BusSchedule'
        db.create_table('program_busschedule', (
            ('id', orm['program.BusSchedule:id']),
            ('program', orm['program.BusSchedule:program']),
            ('src_dst', orm['program.BusSchedule:src_dst']),
            ('departs', orm['program.BusSchedule:departs']),
            ('arrives', orm['program.BusSchedule:arrives']),
        ))
        db.send_create_signal('program', ['BusSchedule'])
        
        # Adding model 'TeacherParticipationProfile'
        db.create_table('program_teacherparticipationprofile', (
            ('id', orm['program.TeacherParticipationProfile:id']),
            ('teacher', orm['program.TeacherParticipationProfile:teacher']),
            ('program', orm['program.TeacherParticipationProfile:program']),
            ('can_help', orm['program.TeacherParticipationProfile:can_help']),
        ))
        db.send_create_signal('program', ['TeacherParticipationProfile'])
        
        # Adding model 'ScheduleConstraint'
        db.create_table('program_scheduleconstraint', (
            ('id', orm['program.ScheduleConstraint:id']),
            ('program', orm['program.ScheduleConstraint:program']),
            ('condition', orm['program.ScheduleConstraint:condition']),
            ('requirement', orm['program.ScheduleConstraint:requirement']),
            ('on_failure', orm['program.ScheduleConstraint:on_failure']),
        ))
        db.send_create_signal('program', ['ScheduleConstraint'])
        
        # Adding model 'ScheduleTestTimeblock'
        db.create_table('program_scheduletesttimeblock', (
            ('booleantoken_ptr', orm['program.ScheduleTestTimeblock:booleantoken_ptr']),
            ('timeblock', orm['program.ScheduleTestTimeblock:timeblock']),
        ))
        db.send_create_signal('program', ['ScheduleTestTimeblock'])
        
        # Adding model 'ProgramCheckItem'
        db.create_table('program_programcheckitem', (
            ('id', orm['program.ProgramCheckItem:id']),
            ('program', orm['program.ProgramCheckItem:program']),
            ('title', orm['program.ProgramCheckItem:title']),
            ('seq', orm['program.ProgramCheckItem:seq']),
        ))
        db.send_create_signal('program', ['ProgramCheckItem'])
        
        # Adding model 'StudentAppReview'
        db.create_table('program_studentappreview', (
            ('id', orm['program.StudentAppReview:id']),
            ('reviewer', orm['program.StudentAppReview:reviewer']),
            ('date', orm['program.StudentAppReview:date']),
            ('score', orm['program.StudentAppReview:score']),
            ('comments', orm['program.StudentAppReview:comments']),
            ('reject', orm['program.StudentAppReview:reject']),
        ))
        db.send_create_signal('program', ['StudentAppReview'])
        
        # Adding model 'ScheduleTestCategory'
        db.create_table('program_scheduletestcategory', (
            ('scheduletesttimeblock_ptr', orm['program.ScheduleTestCategory:scheduletesttimeblock_ptr']),
            ('category', orm['program.ScheduleTestCategory:category']),
        ))
        db.send_create_signal('program', ['ScheduleTestCategory'])
        
        # Adding model 'ClassCategories'
        db.create_table('program_classcategories', (
            ('id', orm['program.ClassCategories:id']),
            ('category', orm['program.ClassCategories:category']),
            ('symbol', orm['program.ClassCategories:symbol']),
        ))
        db.send_create_signal('program', ['ClassCategories'])
        
        # Adding model 'ScheduleTestOccupied'
        db.create_table('program_scheduletestoccupied', (
            ('scheduletesttimeblock_ptr', orm['program.ScheduleTestOccupied:scheduletesttimeblock_ptr']),
        ))
        db.send_create_signal('program', ['ScheduleTestOccupied'])
        
        # Adding model 'SATPrepRegInfo'
        db.create_table('program_satprepreginfo', (
            ('id', orm['program.SATPrepRegInfo:id']),
            ('old_math_score', orm['program.SATPrepRegInfo:old_math_score']),
            ('old_verb_score', orm['program.SATPrepRegInfo:old_verb_score']),
            ('old_writ_score', orm['program.SATPrepRegInfo:old_writ_score']),
            ('diag_math_score', orm['program.SATPrepRegInfo:diag_math_score']),
            ('diag_verb_score', orm['program.SATPrepRegInfo:diag_verb_score']),
            ('diag_writ_score', orm['program.SATPrepRegInfo:diag_writ_score']),
            ('prac_math_score', orm['program.SATPrepRegInfo:prac_math_score']),
            ('prac_verb_score', orm['program.SATPrepRegInfo:prac_verb_score']),
            ('prac_writ_score', orm['program.SATPrepRegInfo:prac_writ_score']),
            ('heard_by', orm['program.SATPrepRegInfo:heard_by']),
            ('user', orm['program.SATPrepRegInfo:user']),
            ('program', orm['program.SATPrepRegInfo:program']),
        ))
        db.send_create_signal('program', ['SATPrepRegInfo'])
        
        # Adding model 'TeacherBio'
        db.create_table('program_teacherbio', (
            ('id', orm['program.TeacherBio:id']),
            ('program', orm['program.TeacherBio:program']),
            ('user', orm['program.TeacherBio:user']),
            ('bio', orm['program.TeacherBio:bio']),
            ('slugbio', orm['program.TeacherBio:slugbio']),
            ('picture', orm['program.TeacherBio:picture']),
            ('picture_height', orm['program.TeacherBio:picture_height']),
            ('picture_width', orm['program.TeacherBio:picture_width']),
            ('last_ts', orm['program.TeacherBio:last_ts']),
        ))
        db.send_create_signal('program', ['TeacherBio'])
        
        # Adding model 'ClassSubject'
        db.create_table('program_class', (
            ('id', orm['program.ClassSubject:id']),
            ('anchor', orm['program.ClassSubject:anchor']),
            ('parent_program', orm['program.ClassSubject:parent_program']),
            ('category', orm['program.ClassSubject:category']),
            ('class_info', orm['program.ClassSubject:class_info']),
            ('allow_lateness', orm['program.ClassSubject:allow_lateness']),
            ('message_for_directors', orm['program.ClassSubject:message_for_directors']),
            ('grade_min', orm['program.ClassSubject:grade_min']),
            ('grade_max', orm['program.ClassSubject:grade_max']),
            ('class_size_min', orm['program.ClassSubject:class_size_min']),
            ('class_size_max', orm['program.ClassSubject:class_size_max']),
            ('schedule', orm['program.ClassSubject:schedule']),
            ('prereqs', orm['program.ClassSubject:prereqs']),
            ('requested_special_resources', orm['program.ClassSubject:requested_special_resources']),
            ('directors_notes', orm['program.ClassSubject:directors_notes']),
            ('requested_room', orm['program.ClassSubject:requested_room']),
            ('session_count', orm['program.ClassSubject:session_count']),
            ('status', orm['program.ClassSubject:status']),
            ('duration', orm['program.ClassSubject:duration']),
        ))
        db.send_create_signal('program', ['ClassSubject'])
        
        # Adding model 'BooleanToken'
        db.create_table('program_booleantoken', (
            ('id', orm['program.BooleanToken:id']),
            ('exp', orm['program.BooleanToken:exp']),
            ('text', orm['program.BooleanToken:text']),
            ('seq', orm['program.BooleanToken:seq']),
        ))
        db.send_create_signal('program', ['BooleanToken'])
        
        # Adding model 'StudentAppResponse'
        db.create_table('program_studentappresponse', (
            ('id', orm['program.StudentAppResponse:id']),
            ('question', orm['program.StudentAppResponse:question']),
            ('response', orm['program.StudentAppResponse:response']),
            ('complete', orm['program.StudentAppResponse:complete']),
        ))
        db.send_create_signal('program', ['StudentAppResponse'])
        
        # Adding model 'ScheduleTestSectionList'
        db.create_table('program_scheduletestsectionlist', (
            ('scheduletesttimeblock_ptr', orm['program.ScheduleTestSectionList:scheduletesttimeblock_ptr']),
            ('section_ids', orm['program.ScheduleTestSectionList:section_ids']),
        ))
        db.send_create_signal('program', ['ScheduleTestSectionList'])
        
        # Adding model 'ClassSection'
        db.create_table('program_classsection', (
            ('id', orm['program.ClassSection:id']),
            ('anchor', orm['program.ClassSection:anchor']),
            ('status', orm['program.ClassSection:status']),
            ('registration_status', orm['program.ClassSection:registration_status']),
            ('duration', orm['program.ClassSection:duration']),
            ('max_class_capacity', orm['program.ClassSection:max_class_capacity']),
            ('parent_class', orm['program.ClassSection:parent_class']),
        ))
        db.send_create_signal('program', ['ClassSection'])
        
        # Adding model 'RegistrationProfile'
        db.create_table('program_registrationprofile', (
            ('id', orm['program.RegistrationProfile:id']),
            ('user', orm['program.RegistrationProfile:user']),
            ('program', orm['program.RegistrationProfile:program']),
            ('contact_user', orm['program.RegistrationProfile:contact_user']),
            ('contact_guardian', orm['program.RegistrationProfile:contact_guardian']),
            ('contact_emergency', orm['program.RegistrationProfile:contact_emergency']),
            ('student_info', orm['program.RegistrationProfile:student_info']),
            ('teacher_info', orm['program.RegistrationProfile:teacher_info']),
            ('guardian_info', orm['program.RegistrationProfile:guardian_info']),
            ('educator_info', orm['program.RegistrationProfile:educator_info']),
            ('last_ts', orm['program.RegistrationProfile:last_ts']),
            ('emailverifycode', orm['program.RegistrationProfile:emailverifycode']),
            ('email_verified', orm['program.RegistrationProfile:email_verified']),
            ('text_reminder', orm['program.RegistrationProfile:text_reminder']),
        ))
        db.send_create_signal('program', ['RegistrationProfile'])
        
        # Adding model 'Program'
        db.create_table('program_program', (
            ('id', orm['program.Program:id']),
            ('anchor', orm['program.Program:anchor']),
            ('grade_min', orm['program.Program:grade_min']),
            ('grade_max', orm['program.Program:grade_max']),
            ('director_email', orm['program.Program:director_email']),
            ('class_size_min', orm['program.Program:class_size_min']),
            ('class_size_max', orm['program.Program:class_size_max']),
            ('program_size_max', orm['program.Program:program_size_max']),
            ('program_allow_waitlist', orm['program.Program:program_allow_waitlist']),
        ))
        db.send_create_signal('program', ['Program'])
        
        # Adding model 'BooleanExpression'
        db.create_table('program_booleanexpression', (
            ('id', orm['program.BooleanExpression:id']),
            ('label', orm['program.BooleanExpression:label']),
        ))
        db.send_create_signal('program', ['BooleanExpression'])
        
        # Adding model 'StudentAppQuestion'
        db.create_table('program_studentappquestion', (
            ('id', orm['program.StudentAppQuestion:id']),
            ('program', orm['program.StudentAppQuestion:program']),
            ('subject', orm['program.StudentAppQuestion:subject']),
            ('question', orm['program.StudentAppQuestion:question']),
            ('directions', orm['program.StudentAppQuestion:directions']),
        ))
        db.send_create_signal('program', ['StudentAppQuestion'])
        
        # Adding model 'StudentApplication'
        db.create_table('program_junctionstudentapp', (
            ('id', orm['program.StudentApplication:id']),
            ('program', orm['program.StudentApplication:program']),
            ('user', orm['program.StudentApplication:user']),
            ('done', orm['program.StudentApplication:done']),
            ('teacher_score', orm['program.StudentApplication:teacher_score']),
            ('director_score', orm['program.StudentApplication:director_score']),
            ('rejected', orm['program.StudentApplication:rejected']),
        ))
        db.send_create_signal('program', ['StudentApplication'])
        
        # Adding model 'ClassImplication'
        db.create_table('program_classimplications', (
            ('id', orm['program.ClassImplication:id']),
            ('cls', orm['program.ClassImplication:cls']),
            ('parent', orm['program.ClassImplication:parent']),
            ('is_prereq', orm['program.ClassImplication:is_prereq']),
            ('enforce', orm['program.ClassImplication:enforce']),
            ('member_ids', orm['program.ClassImplication:member_ids']),
            ('operation', orm['program.ClassImplication:operation']),
        ))
        db.send_create_signal('program', ['ClassImplication'])
        
        # Adding model 'ProgramModule'
        db.create_table('program_programmodule', (
            ('id', orm['program.ProgramModule:id']),
            ('link_title', orm['program.ProgramModule:link_title']),
            ('admin_title', orm['program.ProgramModule:admin_title']),
            ('main_call', orm['program.ProgramModule:main_call']),
            ('module_type', orm['program.ProgramModule:module_type']),
            ('handler', orm['program.ProgramModule:handler']),
            ('seq', orm['program.ProgramModule:seq']),
            ('aux_calls', orm['program.ProgramModule:aux_calls']),
            ('summary_calls', orm['program.ProgramModule:summary_calls']),
            ('required', orm['program.ProgramModule:required']),
        ))
        db.send_create_signal('program', ['ProgramModule'])
        
        # Adding model 'FinancialAidRequest'
        db.create_table('program_financialaidrequest', (
            ('id', orm['program.FinancialAidRequest:id']),
            ('program', orm['program.FinancialAidRequest:program']),
            ('user', orm['program.FinancialAidRequest:user']),
            ('approved', orm['program.FinancialAidRequest:approved']),
            ('reduced_lunch', orm['program.FinancialAidRequest:reduced_lunch']),
            ('household_income', orm['program.FinancialAidRequest:household_income']),
            ('extra_explaination', orm['program.FinancialAidRequest:extra_explaination']),
            ('student_prepare', orm['program.FinancialAidRequest:student_prepare']),
            ('done', orm['program.FinancialAidRequest:done']),
            ('reviewed', orm['program.FinancialAidRequest:reviewed']),
            ('amount_received', orm['program.FinancialAidRequest:amount_received']),
            ('amount_needed', orm['program.FinancialAidRequest:amount_needed']),
        ))
        db.send_create_signal('program', ['FinancialAidRequest'])
        
        # Adding ManyToManyField 'ClassSubject.checklist_progress'
        db.create_table('program_class_checklist_progress', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('classsubject', models.ForeignKey(orm.ClassSubject, null=False)),
            ('programcheckitem', models.ForeignKey(orm.ProgramCheckItem, null=False))
        ))
        
        # Adding ManyToManyField 'ClassSubject.meeting_times'
        db.create_table('program_class_meeting_times', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('classsubject', models.ForeignKey(orm.ClassSubject, null=False)),
            ('event', models.ForeignKey(orm['cal.Event'], null=False))
        ))
        
        # Adding ManyToManyField 'ClassSection.meeting_times'
        db.create_table('program_classsection_meeting_times', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('classsection', models.ForeignKey(orm.ClassSection, null=False)),
            ('event', models.ForeignKey(orm['cal.Event'], null=False))
        ))
        
        # Adding ManyToManyField 'StudentApplication.questions'
        db.create_table('program_junctionstudentapp_questions', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('studentapplication', models.ForeignKey(orm.StudentApplication, null=False)),
            ('studentappquestion', models.ForeignKey(orm.StudentAppQuestion, null=False))
        ))
        
        # Adding ManyToManyField 'Program.class_categories'
        db.create_table('program_program_class_categories', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('program', models.ForeignKey(orm.Program, null=False)),
            ('classcategories', models.ForeignKey(orm.ClassCategories, null=False))
        ))
        
        # Adding ManyToManyField 'ClassSection.checklist_progress'
        db.create_table('program_classsection_checklist_progress', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('classsection', models.ForeignKey(orm.ClassSection, null=False)),
            ('programcheckitem', models.ForeignKey(orm.ProgramCheckItem, null=False))
        ))
        
        # Adding ManyToManyField 'Program.program_modules'
        db.create_table('program_program_program_modules', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('program', models.ForeignKey(orm.Program, null=False)),
            ('programmodule', models.ForeignKey(orm.ProgramModule, null=False))
        ))
        
        # Adding ManyToManyField 'StudentApplication.reviews'
        db.create_table('program_junctionstudentapp_reviews', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('studentapplication', models.ForeignKey(orm.StudentApplication, null=False)),
            ('studentappreview', models.ForeignKey(orm.StudentAppReview, null=False))
        ))
        
        # Adding ManyToManyField 'TeacherParticipationProfile.bus_schedule'
        db.create_table('program_teacherparticipationprofile_bus_schedule', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('teacherparticipationprofile', models.ForeignKey(orm.TeacherParticipationProfile, null=False)),
            ('busschedule', models.ForeignKey(orm.BusSchedule, null=False))
        ))
        
        # Adding ManyToManyField 'StudentApplication.responses'
        db.create_table('program_junctionstudentapp_responses', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('studentapplication', models.ForeignKey(orm.StudentApplication, null=False)),
            ('studentappresponse', models.ForeignKey(orm.StudentAppResponse, null=False))
        ))
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'ArchiveClass'
        db.delete_table('program_archiveclass')
        
        # Deleting model 'BusSchedule'
        db.delete_table('program_busschedule')
        
        # Deleting model 'TeacherParticipationProfile'
        db.delete_table('program_teacherparticipationprofile')
        
        # Deleting model 'ScheduleConstraint'
        db.delete_table('program_scheduleconstraint')
        
        # Deleting model 'ScheduleTestTimeblock'
        db.delete_table('program_scheduletesttimeblock')
        
        # Deleting model 'ProgramCheckItem'
        db.delete_table('program_programcheckitem')
        
        # Deleting model 'StudentAppReview'
        db.delete_table('program_studentappreview')
        
        # Deleting model 'ScheduleTestCategory'
        db.delete_table('program_scheduletestcategory')
        
        # Deleting model 'ClassCategories'
        db.delete_table('program_classcategories')
        
        # Deleting model 'ScheduleTestOccupied'
        db.delete_table('program_scheduletestoccupied')
        
        # Deleting model 'SATPrepRegInfo'
        db.delete_table('program_satprepreginfo')
        
        # Deleting model 'TeacherBio'
        db.delete_table('program_teacherbio')
        
        # Deleting model 'ClassSubject'
        db.delete_table('program_class')
        
        # Deleting model 'BooleanToken'
        db.delete_table('program_booleantoken')
        
        # Deleting model 'StudentAppResponse'
        db.delete_table('program_studentappresponse')
        
        # Deleting model 'ScheduleTestSectionList'
        db.delete_table('program_scheduletestsectionlist')
        
        # Deleting model 'ClassSection'
        db.delete_table('program_classsection')
        
        # Deleting model 'RegistrationProfile'
        db.delete_table('program_registrationprofile')
        
        # Deleting model 'Program'
        db.delete_table('program_program')
        
        # Deleting model 'BooleanExpression'
        db.delete_table('program_booleanexpression')
        
        # Deleting model 'StudentAppQuestion'
        db.delete_table('program_studentappquestion')
        
        # Deleting model 'StudentApplication'
        db.delete_table('program_junctionstudentapp')
        
        # Deleting model 'ClassImplication'
        db.delete_table('program_classimplications')
        
        # Deleting model 'ProgramModule'
        db.delete_table('program_programmodule')
        
        # Deleting model 'FinancialAidRequest'
        db.delete_table('program_financialaidrequest')
        
        # Dropping ManyToManyField 'ClassSubject.checklist_progress'
        db.delete_table('program_class_checklist_progress')
        
        # Dropping ManyToManyField 'ClassSubject.meeting_times'
        db.delete_table('program_class_meeting_times')
        
        # Dropping ManyToManyField 'ClassSection.meeting_times'
        db.delete_table('program_classsection_meeting_times')
        
        # Dropping ManyToManyField 'StudentApplication.questions'
        db.delete_table('program_junctionstudentapp_questions')
        
        # Dropping ManyToManyField 'Program.class_categories'
        db.delete_table('program_program_class_categories')
        
        # Dropping ManyToManyField 'ClassSection.checklist_progress'
        db.delete_table('program_classsection_checklist_progress')
        
        # Dropping ManyToManyField 'Program.program_modules'
        db.delete_table('program_program_program_modules')
        
        # Dropping ManyToManyField 'StudentApplication.reviews'
        db.delete_table('program_junctionstudentapp_reviews')
        
        # Dropping ManyToManyField 'TeacherParticipationProfile.bus_schedule'
        db.delete_table('program_teacherparticipationprofile_bus_schedule')
        
        # Dropping ManyToManyField 'StudentApplication.responses'
        db.delete_table('program_junctionstudentapp_responses')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cal.event': {
            'anchor': ('AjaxForeignKey', ["orm['datatree.DataTree']"], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cal.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.TextField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'cal.eventtype': {
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatree.datatree': {
            'Meta': {'unique_together': "(('name', 'parent'),)"},
            'friendly_name': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lock_table': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'parent': ('AjaxForeignKey', ["orm['datatree.DataTree']"], {'related_name': "'child_set'", 'null': 'True', 'blank': 'True'}),
            'range_correct': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'rangeend': ('django.db.models.fields.IntegerField', [], {}),
            'rangestart': ('django.db.models.fields.IntegerField', [], {}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'uri_correct': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'program.archiveclass': {
            'category': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'date': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_old_students': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'original_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'program': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'student_ids': ('django.db.models.fields.TextField', [], {}),
            'teacher': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'teacher_ids': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'year': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        'program.booleanexpression': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'program.booleantoken': {
            'exp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.BooleanExpression']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'})
        },
        'program.busschedule': {
            'arrives': ('django.db.models.fields.DateTimeField', [], {}),
            'departs': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'src_dst': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'program.classcategories': {
            'category': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'symbol': ('django.db.models.fields.CharField', [], {'default': "'?'", 'max_length': '1'})
        },
        'program.classimplication': {
            'Meta': {'db_table': "'program_classimplications'"},
            'cls': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassSubject']", 'null': 'True'}),
            'enforce': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_prereq': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'member_ids': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '100', 'blank': 'True'}),
            'operation': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['program.ClassImplication']", 'null': 'True'})
        },
        'program.classsection': {
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
            'checklist_progress': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramCheckItem']", 'blank': 'True'}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_class_capacity': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'meeting_times': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cal.Event']", 'blank': 'True'}),
            'parent_class': ('AjaxForeignKey', ["orm['program.ClassSubject']"], {'related_name': "'sections'"}),
            'registration_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'program.classsubject': {
            'Meta': {'db_table': "'program_class'"},
            'allow_lateness': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'anchor': ('AjaxForeignKey', ["orm['datatree.DataTree']"], {}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cls'", 'to': "orm['program.ClassCategories']"}),
            'checklist_progress': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramCheckItem']", 'blank': 'True'}),
            'class_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'class_size_max': ('django.db.models.fields.IntegerField', [], {}),
            'class_size_min': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'directors_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'grade_max': ('django.db.models.fields.IntegerField', [], {}),
            'grade_min': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meeting_times': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cal.Event']", 'blank': 'True'}),
            'message_for_directors': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'parent_program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'prereqs': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requested_room': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requested_special_resources': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'schedule': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'session_count': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'program.financialaidrequest': {
            'amount_needed': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'amount_received': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'approved': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'done': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'extra_explaination': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'household_income': ('django.db.models.fields.CharField', [], {'max_length': '12', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'reduced_lunch': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'reviewed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'student_prepare': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'editable': 'False'})
        },
        'program.program': {
            'anchor': ('AjaxForeignKey', ["orm['datatree.DataTree']"], {}),
            'class_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ClassCategories']"}),
            'class_size_max': ('django.db.models.fields.IntegerField', [], {}),
            'class_size_min': ('django.db.models.fields.IntegerField', [], {}),
            'director_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'grade_max': ('django.db.models.fields.IntegerField', [], {}),
            'grade_min': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program_allow_waitlist': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'program_modules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramModule']"}),
            'program_size_max': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        'program.programcheckitem': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'checkitems'", 'to': "orm['program.Program']"}),
            'seq': ('django.db.models.fields.PositiveIntegerField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'program.programmodule': {
            'admin_title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'aux_calls': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'main_call': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'module_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {}),
            'summary_calls': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'})
        },
        'program.registrationprofile': {
            'contact_emergency': ('AjaxForeignKey', ["orm['users.ContactInfo']"], {'related_name': "'as_emergency'", 'null': 'True', 'blank': 'True'}),
            'contact_guardian': ('AjaxForeignKey', ["orm['users.ContactInfo']"], {'related_name': "'as_guardian'", 'null': 'True', 'blank': 'True'}),
            'contact_user': ('AjaxForeignKey', ["orm['users.ContactInfo']"], {'related_name': "'as_user'", 'null': 'True', 'blank': 'True'}),
            'educator_info': ('AjaxForeignKey', ["orm['users.EducatorInfo']"], {'related_name': "'as_educator'", 'null': 'True', 'blank': 'True'}),
            'email_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'emailverifycode': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'guardian_info': ('AjaxForeignKey', ["orm['users.GuardianInfo']"], {'related_name': "'as_guardian'", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_ts': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2010, 3, 9, 16, 43, 20, 865091)'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'student_info': ('AjaxForeignKey', ["orm['users.StudentInfo']"], {'related_name': "'as_student'", 'null': 'True', 'blank': 'True'}),
            'teacher_info': ('AjaxForeignKey', ["orm['users.TeacherInfo']"], {'related_name': "'as_teacher'", 'null': 'True', 'blank': 'True'}),
            'text_reminder': ('django.db.models.fields.NullBooleanField', [], {'null': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {})
        },
        'program.satprepreginfo': {
            'diag_math_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'diag_verb_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'diag_writ_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'heard_by': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'old_math_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'old_verb_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'old_writ_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'prac_math_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'prac_verb_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'prac_writ_score': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {})
        },
        'program.scheduleconstraint': {
            'condition': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'condition_constraint'", 'to': "orm['program.BooleanExpression']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'on_failure': ('django.db.models.fields.TextField', [], {}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'requirement': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requirement_constraint'", 'to': "orm['program.BooleanExpression']"})
        },
        'program.scheduletestcategory': {
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassCategories']"}),
            'scheduletesttimeblock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['program.ScheduleTestTimeblock']", 'unique': 'True', 'primary_key': 'True'})
        },
        'program.scheduletestoccupied': {
            'scheduletesttimeblock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['program.ScheduleTestTimeblock']", 'unique': 'True', 'primary_key': 'True'})
        },
        'program.scheduletestsectionlist': {
            'scheduletesttimeblock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['program.ScheduleTestTimeblock']", 'unique': 'True', 'primary_key': 'True'}),
            'section_ids': ('django.db.models.fields.TextField', [], {})
        },
        'program.scheduletesttimeblock': {
            'booleantoken_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['program.BooleanToken']", 'unique': 'True', 'primary_key': 'True'}),
            'timeblock': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cal.Event']"})
        },
        'program.studentapplication': {
            'Meta': {'db_table': "'program_junctionstudentapp'"},
            'director_score': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'done': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'questions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.StudentAppQuestion']"}),
            'rejected': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'responses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.StudentAppResponse']"}),
            'reviews': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.StudentAppReview']"}),
            'teacher_score': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'editable': 'False'})
        },
        'program.studentappquestion': {
            'directions': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'question': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassSubject']", 'null': 'True', 'blank': 'True'})
        },
        'program.studentappresponse': {
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.StudentAppQuestion']"}),
            'response': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'program.studentappreview': {
            'comments': ('django.db.models.fields.TextField', [], {}),
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reject': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'reviewer': ('AjaxForeignKey', ["orm['auth.User']"], {'editable': 'False'}),
            'score': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'program.teacherbio': {
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_ts': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'picture': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'picture_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'picture_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'slugbio': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {})
        },
        'program.teacherparticipationprofile': {
            'bus_schedule': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.BusSchedule']"}),
            'can_help': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'teacher': ('AjaxForeignKey', ["orm['auth.User']"], {})
        },
        'users.contactinfo': {
            'address_city': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'address_postal': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'address_state': ('django.contrib.localflavor.us.models.USStateField', [], {'null': 'True', 'blank': 'True'}),
            'address_street': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'address_zip': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'e_mail': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'phone_cell': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'null': 'True', 'blank': 'True'}),
            'phone_day': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'null': 'True', 'blank': 'True'}),
            'phone_even': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'null': 'True', 'blank': 'True'}),
            'undeliverable': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'null': 'True', 'blank': 'True'})
        },
        'users.educatorinfo': {
            'grades_taught': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'school': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'subject_taught': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'null': 'True', 'blank': 'True'})
        },
        'users.guardianinfo': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_kids': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'null': 'True', 'blank': 'True'}),
            'year_finished': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'users.studentinfo': {
            'dob': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'graduation_year': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'heardofesp': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'school': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'studentrep': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'studentrep_expl': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'null': 'True', 'blank': 'True'})
        },
        'users.teacherinfo': {
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'college': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'graduation_year_int': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'major': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'shirt_size': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'shirt_type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['program']
