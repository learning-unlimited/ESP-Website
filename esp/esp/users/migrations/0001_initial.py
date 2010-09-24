
from south.db import db
from django.db import models
from esp.users.models import *

class Migration:
    
    depends_on = (
        ("datatree", "0001_initial"),
    )
    
    def forwards(self, orm):
        
        # Adding model 'TeacherInfo'
        db.create_table('users_teacherinfo', (
            ('id', orm['users.TeacherInfo:id']),
            ('user', orm['users.TeacherInfo:user']),
            ('graduation_year', orm['users.TeacherInfo:graduation_year']),
            ('college', orm['users.TeacherInfo:college']),
            ('major', orm['users.TeacherInfo:major']),
            ('bio', orm['users.TeacherInfo:bio']),
            ('shirt_size', orm['users.TeacherInfo:shirt_size']),
            ('shirt_type', orm['users.TeacherInfo:shirt_type']),
        ))
        db.send_create_signal('users', ['TeacherInfo'])
        
        # Adding model 'UserBitImplication'
        db.create_table('users_userbitimplication', (
            ('id', orm['users.UserBitImplication:id']),
            ('qsc_original', orm['users.UserBitImplication:qsc_original']),
            ('verb_original', orm['users.UserBitImplication:verb_original']),
            ('qsc_implied', orm['users.UserBitImplication:qsc_implied']),
            ('verb_implied', orm['users.UserBitImplication:verb_implied']),
            ('recursive', orm['users.UserBitImplication:recursive']),
        ))
        db.send_create_signal('users', ['UserBitImplication'])
        
        # Adding model 'ZipCode'
        db.create_table('users_zipcode', (
            ('id', orm['users.ZipCode:id']),
            ('zip_code', orm['users.ZipCode:zip_code']),
            ('latitude', orm['users.ZipCode:latitude']),
            ('longitude', orm['users.ZipCode:longitude']),
        ))
        db.send_create_signal('users', ['ZipCode'])
        
        # Adding model 'ESPUser'
        #   Michael Price 9/22/2010: Don't do anything, the auth_user table already exists.
        db.send_create_signal('users', ['ESPUser'])
        
        # Adding model 'PersistentQueryFilter'
        db.create_table('users_persistentqueryfilter', (
            ('id', orm['users.PersistentQueryFilter:id']),
            ('item_model', orm['users.PersistentQueryFilter:item_model']),
            ('q_filter', orm['users.PersistentQueryFilter:q_filter']),
            ('sha1_hash', orm['users.PersistentQueryFilter:sha1_hash']),
            ('create_ts', orm['users.PersistentQueryFilter:create_ts']),
            ('useful_name', orm['users.PersistentQueryFilter:useful_name']),
        ))
        db.send_create_signal('users', ['PersistentQueryFilter'])
        
        # Adding model 'GuardianInfo'
        db.create_table('users_guardianinfo', (
            ('id', orm['users.GuardianInfo:id']),
            ('user', orm['users.GuardianInfo:user']),
            ('year_finished', orm['users.GuardianInfo:year_finished']),
            ('num_kids', orm['users.GuardianInfo:num_kids']),
        ))
        db.send_create_signal('users', ['GuardianInfo'])
        
        # Adding model 'EducatorInfo'
        db.create_table('users_educatorinfo', (
            ('id', orm['users.EducatorInfo:id']),
            ('user', orm['users.EducatorInfo:user']),
            ('subject_taught', orm['users.EducatorInfo:subject_taught']),
            ('grades_taught', orm['users.EducatorInfo:grades_taught']),
            ('school', orm['users.EducatorInfo:school']),
            ('position', orm['users.EducatorInfo:position']),
        ))
        db.send_create_signal('users', ['EducatorInfo'])

        # Adding model 'EmailPref'
        db.create_table('users_emailpref', (
            ('id', orm['users.EmailPref:id']),
            ('email', orm['users.EmailPref:email']),
            ('email_opt_in', orm['users.EmailPref:email_opt_in']),
            ('first_name', orm['users.EmailPref:first_name']),
            ('last_name', orm['users.EmailPref:last_name']),
            ('sms_number', orm['users.EmailPref:sms_number']),
            ('sms_opt_in', orm['users.EmailPref:sms_opt_in']),
        ))
        db.send_create_signal('users', ['EmailPref'])
        
        # Adding model 'PasswordRecoveryTicket'
        db.create_table('users_passwordrecoveryticket', (
            ('id', orm['users.PasswordRecoveryTicket:id']),
            ('user', orm['users.PasswordRecoveryTicket:user']),
            ('recover_key', orm['users.PasswordRecoveryTicket:recover_key']),
            ('expire', orm['users.PasswordRecoveryTicket:expire']),
        ))
        db.send_create_signal('users', ['PasswordRecoveryTicket'])
        
        # Adding model 'ZipCodeSearches'
        db.create_table('users_zipcodesearches', (
            ('id', orm['users.ZipCodeSearches:id']),
            ('zip_code', orm['users.ZipCodeSearches:zip_code']),
            ('distance', orm['users.ZipCodeSearches:distance']),
            ('zipcodes', orm['users.ZipCodeSearches:zipcodes']),
        ))
        db.send_create_signal('users', ['ZipCodeSearches'])
        
        # Adding model 'UserBit'
        db.create_table('users_userbit', (
            ('id', orm['users.UserBit:id']),
            ('user', orm['users.UserBit:user']),
            ('qsc', orm['users.UserBit:qsc']),
            ('verb', orm['users.UserBit:verb']),
            ('startdate', orm['users.UserBit:startdate']),
            ('enddate', orm['users.UserBit:enddate']),
            ('recursive', orm['users.UserBit:recursive']),
        ))
        db.send_create_signal('users', ['UserBit'])
        
        # Adding model 'ESPUser_Profile'
        db.create_table('users_espuser_profile', (
            ('id', orm['users.ESPUser_Profile:id']),
            ('user', orm['users.ESPUser_Profile:user']),
        ))
        db.send_create_signal('users', ['ESPUser_Profile'])
        
        # Adding model 'StudentInfo'
        db.create_table('users_studentinfo', (
            ('id', orm['users.StudentInfo:id']),
            ('user', orm['users.StudentInfo:user']),
            ('graduation_year', orm['users.StudentInfo:graduation_year']),
            ('school', orm['users.StudentInfo:school']),
            ('dob', orm['users.StudentInfo:dob']),
            ('studentrep', orm['users.StudentInfo:studentrep']),
            ('studentrep_expl', orm['users.StudentInfo:studentrep_expl']),
            ('heardofesp', orm['users.StudentInfo:heardofesp']),
        ))
        db.send_create_signal('users', ['StudentInfo'])
        
        # Adding model 'K12School'
        db.create_table('users_k12school', (
            ('id', orm['users.K12School:id']),
            ('contact', orm['users.K12School:contact']),
            ('school_type', orm['users.K12School:school_type']),
            ('grades', orm['users.K12School:grades']),
            ('school_id', orm['users.K12School:school_id']),
            ('contact_title', orm['users.K12School:contact_title']),
            ('name', orm['users.K12School:name']),
        ))
        db.send_create_signal('users', ['K12School'])
        
        # Adding model 'UserAvailability'
        db.create_table('users_useravailability', (
            ('id', orm['users.UserAvailability:id']),
            ('user', orm['users.UserAvailability:user']),
            ('event', orm['users.UserAvailability:event']),
            ('role', orm['users.UserAvailability:role']),
            ('priority', orm['users.UserAvailability:priority']),
        ))
        db.send_create_signal('users', ['UserAvailability'])
        
        # Adding model 'ContactInfo'
        db.create_table('users_contactinfo', (
            ('id', orm['users.ContactInfo:id']),
            ('user', orm['users.ContactInfo:user']),
            ('first_name', orm['users.ContactInfo:first_name']),
            ('last_name', orm['users.ContactInfo:last_name']),
            ('e_mail', orm['users.ContactInfo:e_mail']),
            ('phone_day', orm['users.ContactInfo:phone_day']),
            ('phone_cell', orm['users.ContactInfo:phone_cell']),
            ('phone_even', orm['users.ContactInfo:phone_even']),
            ('address_street', orm['users.ContactInfo:address_street']),
            ('address_city', orm['users.ContactInfo:address_city']),
            ('address_state', orm['users.ContactInfo:address_state']),
            ('address_zip', orm['users.ContactInfo:address_zip']),
            ('address_postal', orm['users.ContactInfo:address_postal']),
            ('undeliverable', orm['users.ContactInfo:undeliverable']),
        ))
        db.send_create_signal('users', ['ContactInfo'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'TeacherInfo'
        db.delete_table('users_teacherinfo')
        
        # Deleting model 'UserBitImplication'
        db.delete_table('users_userbitimplication')
        
        # Deleting model 'ZipCode'
        db.delete_table('users_zipcode')
        
        # Deleting model 'ESPUser'
        db.delete_table('auth_user')
        
        # Deleting model 'PersistentQueryFilter'
        db.delete_table('users_persistentqueryfilter')
        
        # Deleting model 'GuardianInfo'
        db.delete_table('users_guardianinfo')
        
        # Deleting model 'EducatorInfo'
        db.delete_table('users_educatorinfo')
        
        # Deleting model 'EmailPref'
        db.delete_table('users_emailpref')
        
        # Deleting model 'PasswordRecoveryTicket'
        db.delete_table('users_passwordrecoveryticket')
        
        # Deleting model 'ZipCodeSearches'
        db.delete_table('users_zipcodesearches')
        
        # Deleting model 'UserBit'
        db.delete_table('users_userbit')
        
        # Deleting model 'ESPUser_Profile'
        db.delete_table('users_espuser_profile')
        
        # Deleting model 'StudentInfo'
        db.delete_table('users_studentinfo')
        
        # Deleting model 'K12School'
        db.delete_table('users_k12school')
        
        # Deleting model 'UserAvailability'
        db.delete_table('users_useravailability')
        
        # Deleting model 'ContactInfo'
        db.delete_table('users_contactinfo')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cal.event': {
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
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
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_set'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'range_correct': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'rangeend': ('django.db.models.fields.IntegerField', [], {}),
            'rangestart': ('django.db.models.fields.IntegerField', [], {}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'uri_correct': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'users.contactinfo': {
            'address_city': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'address_postal': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'address_state': ('django.contrib.localflavor.us.models.USStateField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'address_street': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'address_zip': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'e_mail': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'phone_cell': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'phone_day': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'phone_even': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'undeliverable': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'users.educatorinfo': {
            'grades_taught': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'school': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'subject_taught': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'users.emailpref': {
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'email_opt_in': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'sms_number': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'sms_opt_in': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'users.espuser_profile': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'users.guardianinfo': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_kids': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'year_finished': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'users.k12school': {
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.ContactInfo']", 'null': 'True', 'blank': 'True'}),
            'contact_title': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'grades': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'school_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'school_type': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'users.passwordrecoveryticket': {
            'expire': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recover_key': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'users.persistentqueryfilter': {
            'create_ts': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_model': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'q_filter': ('django.db.models.fields.TextField', [], {}),
            'sha1_hash': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'useful_name': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'})
        },
        'users.studentinfo': {
            'dob': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'graduation_year': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'heardofesp': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'school': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'studentrep': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'studentrep_expl': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'users.teacherinfo': {
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'college': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'graduation_year': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'major': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'shirt_size': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'shirt_type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'users.useravailability': {
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cal.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'priority': ('django.db.models.fields.DecimalField', [], {'default': "'1.0'", 'max_digits': '3', 'decimal_places': '2'}),
            'role': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'users.userbit': {
            'enddate': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(9999, 1, 1, 0, 0)', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'qsc': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'userbit_qsc'", 'to': "orm['datatree.DataTree']"}),
            'recursive': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'startdate': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'verb': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'userbit_verb'", 'to': "orm['datatree.DataTree']"})
        },
        'users.userbitimplication': {
            'created_bits': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['users.UserBit']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'qsc_implied': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'qsc_implied'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'qsc_original': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'qsc_original'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'recursive': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'verb_implied': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'verb_implied'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'verb_original': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'verb_original'", 'null': 'True', 'to': "orm['datatree.DataTree']"})
        },
        'users.zipcode': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '6'}),
            'longitude': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '6'}),
            'zip_code': ('django.db.models.fields.CharField', [], {'max_length': '5'})
        },
        'users.zipcodesearches': {
            'distance': ('django.db.models.fields.DecimalField', [], {'max_digits': '15', 'decimal_places': '3'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'zip_code': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.ZipCode']"}),
            'zipcodes': ('django.db.models.fields.TextField', [], {})
        }
    }
    
    complete_apps = ['users']
