from django import forms
from django.contrib.localflavor.us.forms import USStateField, USPhoneNumberField, USStateSelect
from esp.customforms.forms import NameField, AddressField

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