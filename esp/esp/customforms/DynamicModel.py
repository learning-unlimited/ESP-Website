from django.db import models
from south.db import db
from django.db.models.loading import cache
from django.db import transaction
from esp.customforms.models import Field

class DynamicModelHandler:
	"""Handler class for creating, modifying and deleting dynamic models
		-Uses South for db operations
		- __init__() takes as input two arguments -> 'form', the current Form instance, and 'fields', 
			a list of (field_id, field_type) tuples
	"""
	
	_app_label='customforms'
	_module='esp.customforms.models'
	
	_field_types={
		'textField':{'max_length':30,},
		'longTextField':{'max_length':60,},
		'longAns':{},
		'reallyLongAns':{},
		'radio':{'max_length':50,},
		'dropdown':{'max_length':50,},
		'numeric':{},
		'date':{},
		'time':{},
		'first_name':{'max_length':30,},
		'last_name':{'max_length':30,},
		'gender':{'max_length':1,},
		'phone':{'max_length':15,},
		'email':{'max_length':30,},
		'street_address':{'max_length':100,},
		'state':{'max_length':20,},
		'city':{'max_length':30,},
		'zip':{'max_length':5,},
		'courses':{'max_length':100,},
	}
	
	_customFields={
		'name':['first_name', 'last_name'],
		'address':['street_address', 'state', 'city', 'zip'],
	}
	
	def __init__(self, form=None, fields=[]):
		self.form=form
		self.field_list=[]
		self.fields=fields
		
	def _getFieldsForForm(self):
		"""Gets the list of (field_id, field_type) tuples for the present form.
			Called if this list isn't passed to __init__() and the dynamic model needs to be generated.
		"""
		self.fields=Field.objects.filter(form=self.form).values_list('id', 'field_type')
		return self.fields	
	
	def _getModelField(self, field_type):
		"""Returns the appropriate Django Model Field based on field_type"""
		
		if field_type=='longAns' or field_type=='reallyLongAns':
			return models.TextField()
		elif field_type=='numeric':
			return models.IntegerField(null=True)
		elif field_type=='date':
			return models.DateField(null=True)
		elif field_type=='time':
			return models.TimeField(null=True)
		else:
			return models.CharField(max_length=self._field_types[field_type]['max_length'])
			
	def _getModelFieldList(self):
		"""Returns a list of Model Field tuples given a list of field_types (from the metadata)
			-An entry would be like (field_name, field)
			-An 'id' field is automatically added, as is a 'user_id' field, based on whether the form
			is anonymous or not.
			-A field-name is of the form 'question_23', where '23' is the ID of the corresponding question
			-For custom fields like address, a field-name would be of the form 'question_23_zip'
		"""
		if not self.fields:
			self._getFieldsForForm()
		
		self.field_list.append( ('id', models.AutoField(primary_key=True) ) )
		if not self.form.anonymous:
			self.field_list.append( ('user_id', models.IntegerField() ) )
		for field_id, field in self.fields:
			if field in self._customFields:
				for f in self._customFields[field]:
					self.field_list.append( ('question_'+str(field_id)+'_'+f, self._getModelField(f) ) )
			else:
				self.field_list.append( ('question_'+str(field_id), self._getModelField(field) ) )	
		return self.field_list
		
	def createTable(self):
		"""Sets up the database table using self.field_list"""
		
		if not self.field_list:
			self._getModelFieldList()
		
		if not transaction.is_managed:
			db.start_transaction()
			db.create_table('customforms_response_%d' % self.form.id, tuple(self.field_list))
			db.commit_transaction()
		else:
			db.create_table('customforms_response_%d' % self.form.id, tuple(self.field_list))	
		
	def deleteTable(self):
		"""Deletes the response table for the current form"""
		
		db.start_transaction()
		db.delete_table('customforms_response_%d' % self.form.id)
		db.commit_transaction()		
	
	def createDynModel(self):
		"""Creates and returns the dynamic model for this form"""
		
		_db_table='customforms_response_%d' % self.form.id
		_model_name='Response_%d' % self.form.id
		
		#Removing any existing model definitions from Django's cache
		try:
			del cache.app_models[self._app_label][_model_name.lower()]
		except KeyError:
			pass
			
		class Meta:
			app_label=self._app_label
			db_table=_db_table
		
		attrs={'__module__':self._module, 'Meta': Meta}
		
		#Updating attrs with the fields
		if not self.field_list:				
			self._getModelFieldList()
		attrs.update(dict(self.field_list))
		
		dynModel=type(_model_name, (models.Model,), attrs)
		return dynModel	
				
		
		
		
						
				
		
								