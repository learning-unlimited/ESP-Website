
from south.db import db
from django.db import models
from esp.program.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Changing field 'ArchiveClass.category'
        # (to signature: django.db.models.fields.CharField(max_length=32))
        db.alter_column('program_archiveclass', 'category', orm['program.archiveclass:category'])
        
    
    
    def backwards(self, orm):
        
        # Changing field 'ArchiveClass.category'
        # (to signature: django.db.models.fields.CharField(max_length=16))
        db.alter_column('program_archiveclass', 'category', orm['program.archiveclass:category'])
        
    
    
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
            'category': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
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
            'last_ts': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2010, 3, 9, 16, 55, 15, 900068)'}),
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
