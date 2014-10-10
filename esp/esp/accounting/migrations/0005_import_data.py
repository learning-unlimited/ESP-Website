# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django import db as django_db

from esp.accounting_docs.models import Document
from esp.program.models import Program
from esp.users.models import ESPUser

from esp.accounting.controllers import GlobalAccountingController, IndividualAccountingController, ProgramAccountingController

from decimal import Decimal

def migrate_program(program):

	docs = Document.objects.filter(anchor=program.anchor, doctype=2)
	num_uncategorized = 0
	num = 0
	found_for_program = False
	student_dict = {}

	#   Clear financial data for this program
	pac = ProgramAccountingController(program)
	pac.clear_all_data()
	lineitem_types = {'one': {}, 'multi': {}, 'select': []}
	lineitem_choices = {}
		
	#   Build a database of each student's financial transactions for the program
	for doc in docs:
		student_id = doc.user.id

		if student_id not in student_dict:
			student_dict[student_id] = {
				'admission': {},
				'finaid_amt': Decimal('0'),
				'items': [],
				'items_select': [],
				'payment': [],
			}
		lineitems = doc.txn.lineitem_set.all()
		"""
		if lineitems.count() > 0:
			try:
				print '\nStudent: %s' % doc.user.name()
			except:
				print '\nStudent: %s' % doc.user.username
		"""
		for li in lineitems:
			found_for_program = True
			base_txt = '[%5d] %s: %.2f' % (li.id, li.text, li.amount)
			#   if li.anchor.uri == splash.anchor.uri + '/LineItemTypes/Required':
			if 'admission' in li.text.lower() or 'cost of attending' in li.text.lower():
				base_txt = '(Admission) ' + base_txt
				if li.text not in student_dict[student_id]['admission']:
					student_dict[student_id]['admission'][li.text] = li.amount.copy_abs()
			elif 'financial aid' in li.text.lower():
				base_txt = '(Finaid) ' + base_txt
				student_dict[student_id]['finaid_amt'] += li.amount
			elif 'payment received' in li.text.lower():
				base_txt = '(Payment) ' + base_txt
				student_dict[student_id]['payment'].append(li.amount.copy_abs())
			elif 'expecting on-site payment' in li.text.lower():
				base_txt = '(Payment expected) ' + base_txt
				student_dict[student_id]['payment'].append(li.amount.copy_abs())
			elif 'BuyMultiSelect' in li.anchor.uri:
				base_txt = '(Select: field "%s", choice "%s") ' % (li.anchor.name, li.text) + base_txt
				student_dict[student_id]['items_select'].append((li.anchor.name, li.text, li.amount.copy_abs()))
				if li.anchor.name not in lineitem_types['select']:
					lineitem_types['select'].append(li.anchor.name)
					lineitem_choices[li.anchor.name] = []
				if (li.text, li.amount.copy_abs()) not in lineitem_choices[li.anchor.name]:
					lineitem_choices[li.anchor.name].append((li.text, li.amount.copy_abs()))
			elif 'BuyMany' in li.anchor.uri or 'shirt' in li.text.lower():
				base_txt = '(Multi: field "%s") ' % (li.anchor.name) + base_txt
				student_dict[student_id]['items'].append((li.text, li.amount.copy_abs()))
				if li.text not in lineitem_types['multi']:
					lineitem_types['multi'][li.text] = li.amount.copy_abs()
			elif 'BuyOne' in li.anchor.uri or 'lunch' in li.text.lower() or 'dinner' in li.text.lower() or 'photo' in li.text.lower():
				base_txt = '(Single: field "%s") ' % (li.anchor.name) + base_txt
				student_dict[student_id]['items'].append((li.text, li.amount.copy_abs()))
				if li.text not in lineitem_types['one']:
					lineitem_types['one'][li.text] = li.amount.copy_abs()
			else:
				num_uncategorized += 1
				print 'WARNING: Uncategorized line item: %s' % base_txt
				#   raise Exception('Uncategorized line item: %s' % base_txt)
				
			num += 1
			#   print '-- %s' % base_txt 
		"""
		if student_dict[student_id]['finaid_amt'] > 0:
			print student_dict[student_id]
		elif len(student_dict[student_id]['items_multi']) > 0:
			print student_dict[student_id]
		"""
		
	if found_for_program:
		num_programs = 1
	else:
		num_programs = 0
	
	#   Populate line item types for the program
	optional_items = []
	for item in lineitem_types['one']:
		optional_items.append((item, lineitem_types['one'][item], 1))
	for item in lineitem_types['multi']:
		optional_items.append((item, lineitem_types['multi'][item], 10))
	select_items = []
	for item in lineitem_types['select']:
		select_items.append((item, lineitem_choices[item]))
	
	#   print optional_items
	#   print select_items
	pac.setup_accounts()
	pac.setup_lineitemtypes(0.0, optional_items, select_items)
	
	#   Create new transfer records for this student
	for student_id in student_dict:
		user = ESPUser.objects.get(id=student_id)
		iac = IndividualAccountingController(program, user)
		rec = student_dict[student_id]
		
		#   Admission fee
		admission_total_cost = 0
		for key in rec['admission']:
			admission_total_cost += rec['admission'][key]
		if admission_total_cost > 0:
			initial_transfer = iac.add_required_transfers()[0]
			initial_transfer.amount_dec = admission_total_cost
			initial_transfer.save()
			
		#   Financial aid
		if rec['finaid_amt'] > 0:
			if rec['finaid_amt'] >= admission_total_cost:
				iac.grant_full_financial_aid()
			else:
				iac.set_finaid_params(rec['finaid_amt'], None)
		
		#   Optional items
		prefs = []
		for item in rec['items']:
			prefs.append((item[0], 1, item[1]))
		for item in rec['items_select']:
			prefs.append((item[0], 1, item[2]))
		iac.apply_preferences(prefs)
		
		#   Payments
		for payment in rec['payment']:
			iac.submit_payment(payment)
	
	try:
		attended_ids = program.students()['attended'].values_list('id', flat=True)

		#   Execute transfers for the students that are marked as attended
		pac.execute_pending_transfers(ESPUser.objects.filter(id__in=attended_ids))

		#   Clear transfers for the students that are marked as not attended
		pac.remove_pending_transfers(ESPUser.objects.exclude(id__in=attended_ids))
	except:
		print 'Unable to determine which students attended the program; all transfers remain unexecuted'

	print 'Converted %d line items for %s; %d uncategorized' % (num, program.niceName(), num_uncategorized)
	return num_programs

class Migration(SchemaMigration):

    def forwards(self, orm):

        gac = GlobalAccountingController()
        gac.setup_accounts()

        num_programs = 0
        for program in Program.objects.all():
            print '\nConverting financial data for %s' % program.niceName()
            num_programs += migrate_program(program)
            django_db.reset_queries()
            
        print 'Converted financial data for %d programs' % num_programs

    def backwards(self, orm):
        pass

    models = {
        'accounting.account': {
            'Meta': {'unique_together': "(('name',),)", 'object_name': 'Account'},
            'balance_dec': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '9', 'decimal_places': '2'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'})
        },
        'accounting.financialaidgrant': {
            'Meta': {'unique_together': "(('request',),)", 'object_name': 'FinancialAidGrant'},
            'amount_max_dec': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '2', 'blank': 'True'}),
            'finalized': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'percent': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.FinancialAidRequest']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'accounting.lineitemoptions': {
            'Meta': {'object_name': 'LineItemOptions'},
            'amount_dec': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '2', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lineitem_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting.LineItemType']"})
        },
        'accounting.lineitemtype': {
            'Meta': {'object_name': 'LineItemType'},
            'amount_dec': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '2', 'blank': 'True'}),
            'for_finaid': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'for_payments': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_quantity': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'accounting.transfer': {
            'Meta': {'object_name': 'Transfer'},
            'amount_dec': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'destination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'transfer_destination'", 'null': 'True', 'to': "orm['accounting.Account']"}),
            'executed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_item': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting.LineItemType']", 'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'transfer_source'", 'null': 'True', 'to': "orm['accounting.Account']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatree.datatree': {
            'Meta': {'unique_together': "(('name', 'parent'),)", 'object_name': 'DataTree'},
            'friendly_name': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lock_table': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_set'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'range_correct': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rangeend': ('django.db.models.fields.IntegerField', [], {}),
            'rangestart': ('django.db.models.fields.IntegerField', [], {}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'uri_correct': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'program.classcategories': {
            'Meta': {'object_name': 'ClassCategories'},
            'category': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'symbol': ('django.db.models.fields.CharField', [], {'default': "'?'", 'max_length': '1'})
        },
        'program.financialaidrequest': {
            'Meta': {'unique_together': "(('program', 'user'),)", 'object_name': 'FinancialAidRequest'},
            'done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'extra_explaination': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'household_income': ('django.db.models.fields.CharField', [], {'max_length': '12', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'reduced_lunch': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'student_prepare': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'program.program': {
            'Meta': {'object_name': 'Program'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'unique': 'True'}),
            'class_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ClassCategories']", 'symmetrical': 'False'}),
            'director_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'grade_max': ('django.db.models.fields.IntegerField', [], {}),
            'grade_min': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'program_allow_waitlist': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'program_modules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramModule']", 'symmetrical': 'False'}),
            'program_size_max': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'program.programmodule': {
            'Meta': {'object_name': 'ProgramModule'},
            'admin_title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'handler': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inline_template': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'link_title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'module_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'seq': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['accounting']