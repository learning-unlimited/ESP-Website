from esp.customforms.models import *
from django import forms
from form_utils.forms import BetterForm
from django.utils.datastructures import SortedDict
from django.contrib.formtools.wizard import FormWizard
from django.shortcuts import redirect, render_to_response, HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.localflavor.us.forms import USStateField, USPhoneNumberField, USStateSelect
from esp.customforms.forms import CourseSelect, NameField, AddressField
from esp.customforms.DynamicModel import DynamicModelHandler as DMH
from esp.users.models import ContactInfo

class BaseCustomForm(BetterForm):
	"""
	This is the base class for all custom forms.
	"""
	def clean(self):
		"""
		This takes cleaned_data and expands the values for combo fields
		"""
		cleaned_data=self.cleaned_data.copy()
		for k,v in self.cleaned_data.items():
			if isinstance(v, dict):
				cleaned_data.update(v)
				del cleaned_data[k]
		return cleaned_data		
		

class CustomFormHandler():
	"""Handles creation of 'one' Django form (=one page)"""
	
	_field_types={
		'textField':{'typeMap': forms.CharField, 'attrs':{'widget':forms.TextInput,}, 'widget_attrs':{'size':'30',}},
		'longTextField':{'typeMap': forms.CharField, 'attrs':{'widget':forms.TextInput,}, 'widget_attrs':{'size':'60',}},
		'longAns':{'typeMap': forms.CharField, 'attrs':{'widget':forms.Textarea,}, 'widget_attrs':{'rows':'8', 'cols':'50',}},
		'reallyLongAns':{'typeMap': forms.CharField, 'attrs':{'widget':forms.Textarea,}, 'widget_attrs':{'rows':'14', 'cols':'70',}},
		'radio':{'typeMap': forms.ChoiceField, 'attrs':{'widget': forms.RadioSelect, }, 'widget_attrs':{}},
		'dropdown':{'typeMap': forms.ChoiceField, 'attrs':{'widget': forms.Select, }, 'widget_attrs':{}},
		'multiselect':{'typeMap': forms.MultipleChoiceField, 'attrs':{'widget': forms.SelectMultiple, }, 'widget_attrs':{}},
		'checkboxes':{'typeMap': forms.MultipleChoiceField, 'attrs':{'widget': forms.CheckboxSelectMultiple, }, 'widget_attrs':{}},
		'numeric':{'typeMap': forms.IntegerField, 'attrs':{}, 'widget_attrs':{},},
		'date':{'typeMap': forms.DateField,'attrs':{}, 'widget_attrs':{},},
		'time':{'typeMap': forms.TimeField, 'attrs':{}, 'widget_attrs':{},},
		'name':{'typeMap':NameField, 'attrs':{}, 'widget_attrs':{}},
		'gender':{'typeMap': forms.ChoiceField, 'attrs':{'widget':forms.RadioSelect, 'choices':[('M','Male'), ('F', 'Female')]}, 'widget_attrs':{}},
		'phone':{'typeMap': USPhoneNumberField, 'attrs':{}, 'widget_attrs':{}},
		'email':{'typeMap': forms.EmailField, 'attrs':{'max_length':30,}, 'widget_attrs':{}},
		'address':{'typeMap':AddressField, 'attrs':{}, 'widget_attrs':{}},
		'street':{'typeMap': forms.CharField, 'attrs':{'max_length':100,}, 'widget_attrs':{}},
		'state':{'typeMap': USStateField, 'attrs':{'widget': USStateSelect}, 'widget_attrs':{}},
		'city':{'typeMap': forms.CharField, 'attrs':{'max_length':50,}, 'widget_attrs':{},},
		'zip':{'typeMap': forms.CharField, 'attrs':{'max_length':5,}, 'widget_attrs':{}},
		'courses':{'typeMap': forms.ChoiceField, 'attrs':{'widget':CourseSelect}, 'widget_attrs':{}},
	}
	
	_field_attrs=['label', 'help_text', 'required']
	
	_contactinfo_map={
		'name':['first_name', 'last_name'],
		'email':'e_mail',
		'phone':'phone_day',
		'address':['address_street', 'address_city', 'address_state', 'address_zip'],
		'street':'address_street',
		'city':'address_city',
		'zip':'address_zip',
		'state':'address_state'
	}
	
	_combo_fields=['name', 'address']
	
	def __init__(self, page=None, form=None):
		self.page=page
		self.form=form
		self.fields=[]
		self.fieldsets=[]
		self.initial={}
		
	def _getAttrs(self, attrs):
		"""Takes attrs from the metadata and returns its Django equivalent"""
		
		other_attrs={}
		for attr in attrs:
			if attr['attr_type']=='options':
				other_attrs['choices']=[]
				options_list=attr['value'].split('|')[:-1]
				for option in options_list:
					other_attrs['choices'].append( (option, option) )
			elif attr['attr_type']=='limits':
				limits=attr['value'].split(',')
				if limits[0]:
					other_attrs['min_value']=int(limits[0])
				if limits[1]:
					other_attrs['max_value']=int(limits[1])
		return other_attrs				 			
		
	def _populateFields(self):
		
		"""Populates self.fields and self.fieldsets with the appropriate Form fields"""
		
		sections=Section.objects.filter(page=self.page).order_by('seq').values('id', 'title','description')
		for section in sections:
			curr_fieldset=[]
			curr_fieldset.extend([section['title'], {'fields':[]}])
			curr_fieldset[1]['description']=section['description']
			
			fields=Field.objects.filter(form=self.form, section=section['id']).order_by('seq').values('id', 'field_type', 'label', 'help_text', 'required')
			for field in fields:
				field_name='question_%d' % field['id']
				field_attrs=field.copy()
				
				#Checking if it needs to be pre-populated with initial data during rendering.
				if field['field_type'] in self._contactinfo_map:
					self.initial[field_name]=self._contactinfo_map[field['field_type']]
				
				#Setting the 'name' attribute for combo fields
				if field_attrs['field_type'] in self._combo_fields:
					field_attrs['name']=field_name
					
				del field_attrs['id'], field_attrs['field_type']
				other_attrs=Attribute.objects.filter(field=field['id']).values('attr_type', 'value')
				if other_attrs:
					field_attrs.update(self._getAttrs(other_attrs))
				field_attrs.update(self._field_types[field['field_type']]['attrs'])
				if field['field_type']=='courses':
					if self.form.link_type=='program':
						field_attrs['widget']=field_attrs['widget'](program=Program.objects.get(pk=int(self.form.link_id)))
				else:		
					try:
						field_attrs['widget']=field_attrs['widget'](attrs=self._field_types[field['field_type']]['widget_attrs'])
					except KeyError:
						pass
					
				self.fields.append([field_name, self._field_types[field['field_type']]['typeMap'](**field_attrs) ])
				curr_fieldset[1]['fields'].append(field_name)
			self.fieldsets.append(tuple(curr_fieldset))
			
	def getForm(self):
		""" Returns the BetterForm class for the current page"""
		_form_name="page_%d" % self.page.id
		
		if not self.fields:
			self._populateFields()
		
		class Meta:
			fieldsets=self.fieldsets
		
		attrs={'Meta':Meta}
		attrs.update(SortedDict(self.fields))	
		
		self.page_form=type(_form_name, (BaseCustomForm,), attrs)
		return self.page_form
		
class ComboForm(FormWizard):
	
	def __init__(self, form_list, form, initial=None):
		self.form=form
		super(ComboForm, self).__init__(form_list, initial)
	
	def get_template(self, step):
		return 'customforms/playing.html'
	
	def done(self, request, form_list):
		data={}
		for form in form_list:
			data.update(form.cleaned_data)
		#Plonking in user_id if the form is non-anonymous
		if not self.form.anonymous:
			data['user_id']=request.user.id
		#Generating the dynamic model and saving the response		
		dyn=DMH(form=self.form)
		dynModel=dyn.createDynModel()
		dynModel.objects.create(**data)	
		return HttpResponseRedirect('/customforms/success/')
		
	def prefix_for_step(self, step):
		"""The FormWizard implements a form prefix for each step. Setting the prefix to an empty string, 
		as the field name is already unique"""
		return ''			
		
class FormHandler:
	"""Handles creation of a form (single page or multi-page). Uses Django's FormWizard."""
	
	def __init__(self, form, user=None):
		self.form=form
		self.form_list=[]
		self.wizard=None
		self.user=user
		self.initial={}
		
	def _populateFormList(self):
		"""Populates self.form_list with the BetterForm sub-classes corresponding to each page"""
		
		pages=Page.objects.filter(form=self.form).order_by('seq')
		for page in pages:
			cfh=CustomFormHandler(page=page, form=self.form)
			self.form_list.append(cfh.getForm())
			
			#Setting intitial data for this page/step
			if cfh.initial:
				self.initial[page.seq]={}
				user_info=ContactInfo.objects.filter(user=self.user).values()[0]
				for k,v in cfh.initial.items():
					#Compound fields need to be initialized with a list of values
					if isinstance(v, (list)):
						self.initial[page.seq].update({k:[user_info[key] for key in v]})
					else:
						self.initial[page.seq].update({k:user_info[v]})
	
	def getWizard(self):
		"""Returns the ComboForm instance for this form"""
		if not self.form_list:
			self._populateFormList()
		self.wizard=ComboForm(self.form_list, self.form, self.initial)	
		return self.wizard
		
	def deleteForm(self):
		"""Deletes all information relating to the form from the db.
			Also removes the response table
		"""
		dyn=DMH(form=self.form)
		dyn.deleteTable()
		self.form.delete() #Cascading Foreign Keys should take care of everything
				
		
											
					
				
			
			 
			
			
	
	