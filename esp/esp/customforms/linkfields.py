from django import forms
from django.forms.models import fields_for_model
from django.db.models.loading import get_models
from django.contrib.localflavor.us.forms import USStateField, USPhoneNumberField, USStateSelect
from esp.customforms.forms import NameField, AddressField

generic_fields={
	'textField':{'typeMap': forms.CharField, 'attrs':{'widget':forms.TextInput,}, 'widget_attrs':{'size':'30', 'class':''}},
	'longTextField':{'typeMap': forms.CharField, 'attrs':{'widget':forms.TextInput,}, 'widget_attrs':{'size':'60', 'class':''}},
	'longAns':{'typeMap': forms.CharField, 'attrs':{'widget':forms.Textarea,}, 'widget_attrs':{'rows':'8', 'cols':'50', 'class':''}},
	'reallyLongAns':{'typeMap': forms.CharField, 'attrs':{'widget':forms.Textarea,}, 'widget_attrs':{'rows':'14', 'cols':'70', 'class':''}},
	'radio':{'typeMap': forms.ChoiceField, 'attrs':{'widget': forms.RadioSelect, }, 'widget_attrs':{'class':''}},
	'dropdown':{'typeMap': forms.ChoiceField, 'attrs':{'widget': forms.Select, }, 'widget_attrs':{'class':''}},
	'multiselect':{'typeMap': forms.MultipleChoiceField, 'attrs':{'widget': forms.SelectMultiple, }, 'widget_attrs':{'class':''}},
	'checkboxes':{'typeMap': forms.MultipleChoiceField, 'attrs':{'widget': forms.CheckboxSelectMultiple, }, 'widget_attrs':{'class':''}},
	'numeric':{'typeMap': forms.IntegerField, 'attrs':{'widget':forms.TextInput,}, 'widget_attrs':{'class':'digits'},},
	'date':{'typeMap': forms.DateField,'attrs':{'widget':forms.DateInput,}, 'widget_attrs':{'class':'ddate', 'format':'%m-%d-%Y'},},
	'time':{'typeMap': forms.TimeField, 'attrs':{'widget':forms.TimeInput,}, 'widget_attrs':{'class':'time'},},
}

class CustomFormsLinkModel(object):
	#Dummy class to identify linked models with
	pass
	
class CustomFormsCache:
	#Holds a global cache of all models and fields
	#available to customforms.
	#Uses the Borg design pattern like Django's AppCache class.
	
	__shared_state=dict(
		only_fkey_models={},
		link_fields={},
		loaded=False,
	)
	
	def __init__(self):
		self.__dict__=self.__shared_state
		
	def _populate(self):
		"""
		Populates the cache with metadata about models
		"""
		if self.loaded:
			return
			
		for model in get_models():
			if CustomFormsLinkModel in model.__bases__:
				if not hasattr(model, 'link_fields_list'):
					#only_fkey model
					self.only_fkey_models.update({model.form_link_name : model})
				else:
					#This model has linked fields	
					self.link_fields[model.form_link_name]={'model':model, 'fields':{}}
					#Now getting the fields
					all_form_fields=fields_for_model(model, widgets=getattr(model, 'link_fields_widgets', None))
					sublist=getattr(model, 'link_fields_list')
					for field, display_name in sublist:
						field_name=model.__name__ + "_" + field
						field_instance=all_form_fields[field]
						generic_field_type=self._getGenericType(field_instance.widget)
						self.link_fields[model.form_link_name]['fields'].update({ field_name:{
							'model_field':field,
							'disp_name':display_name,
							'field_type':generic_field_type,
							'ques':field_instance.label, #default label
							'required':field_instance.required,
						}
						})
		
		self.loaded=True				
						
	def _getGenericType(self, widget):
		"""
		Returns the generic field type (e.g. textField) corresponding to this widget.
		This information is useful for rendering this field in the form builder.
		If this field doesn't resemble any of the generic fields, we return 'custom'.
		A match is taken if the widget is the same as that of a generic field, or is a subclass.
		TODO -> USStateField ???
		Note-> It's not currently accurate, as it only compares widgets, but since it's only used for preview purposes in
		the form builder, it shouldn't matter.
		"""					
		for k,v in generic_fields.items():
			if widget is v['attrs']['widget'] or (widget.__class__ is v['attrs']['widget']):
				return k
			try:
				if v['attrs']['widget'] in widget.__bases__:
					return k
			except AttributeError:
				if v['attrs']['widget'] in widget.__class__.__bases__:
					return k		
		return 'custom'
	
	def isLinkField(self, field):
		"""
		Convenience method to get check if 'field' is a link field
		"""	
		if field not in generic_fields: return True	
		else: return False 
	
	def getLinkFieldData(self, field):
		"""
		Convenience method to get data for a particular linked field
		"""
		for category, options in self.link_fields.items():
			if field in options['fields']: return options['fields'][field]
				
	def modelForLinkField(self, field):
		"""
		Returns the model associated with a particular link field.
		"""
		for category, options in self.link_fields.items():
			if field in options['fields']: return options['model']					
				
cf_cache=CustomFormsCache()								
		
#The following is redundant for now
link_fields={
	'first_name':{
		'model':'users.contactinfo',
		'model_field':'first_name',
		'form_fld_props':{'typeMap':forms.CharField, 'attrs':{}, 'widget_attrs':{'class':''}},
	},
	'last_name':{
		'model':'users.contactinfo',
		'model_field':'last_name',
		'form_fld_props':{'typeMap':forms.CharField, 'attrs':{}, 'widget_attrs':{'class':''}},
	},
	'email':{
		'model':'users.contactinfo',
		'model_field':'e_mail',
		'form_fld_props':{'typeMap': forms.EmailField, 'attrs':{'max_length':30, 'widget':forms.TextInput,}, 'widget_attrs':{'class':'email'}},
	},
	'phone':{
		'model':'users.contactinfo',
		'model_field':'phone_day',
		'form_fld_props':{'typeMap': USPhoneNumberField, 'attrs':{'widget':forms.TextInput,}, 'widget_attrs':{'class':'USPhone'}},
	},
	'street':{
		'model':'users.contactinfo',
		'model_field':'address_street',
		'form_fld_props':{'typeMap': forms.CharField, 'attrs':{'max_length':100, 'widget':forms.TextInput,}, 'widget_attrs':{'class':''}},
	},
	'city':{
		'model':'users.contactinfo',
		'model_field':'address_city',
		'form_fld_props':{'typeMap': forms.CharField, 'attrs':{'max_length':50, 'widget':forms.TextInput,}, 'widget_attrs':{'class':''},},
	},
	'state':{
		'model':'users.contactinfo',
		'model_field':'address_state',
		'form_fld_props':{'typeMap': USStateField, 'attrs':{'widget': USStateSelect}, 'widget_attrs':{'class':''}},
	},
	'zip':{
		'model':'users.contactinfo',
		'model_field':'address_zip',
		'form_fld_props':{'typeMap': forms.CharField, 'attrs':{'max_length':5, 'widget':forms.TextInput,}, 'widget_attrs':{'class':'USZip'}},
	},
	'name':{
		'model':'users.contactinfo',
		'combo':['first_name', 'last_name'],
		'form_fld_props':{'typeMap':NameField, 'attrs':{}, 'widget_attrs':{'class':''}},
	},
	'address':{
		'model':'users.contactinfo',
		'combo':['street', 'city', 'state', 'zip'],
		'form_fld_props':{'typeMap':AddressField, 'attrs':{}, 'widget_attrs':{'class':''}},
	},
}

only_fkey_models={
	#Models that can only be foreign-keyed to, and not modified.
	#Keys are displayed in the form builder.
	#disp_name, used to show a nice name for instances, can be an attribute or a method (i.e. callable)
	'Program':{'model':'program.program', 'disp_name':'niceName'},
	'Course':{'model':'program.classsubject', 'disp_name':'title'},
}