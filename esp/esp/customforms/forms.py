from django.forms.fields import Select
from django import forms
from django.utils.datastructures import SortedDict
from django.contrib.localflavor.us.forms import USStateField, USStateSelect

choices=[(1,1), (2,2),]

class CourseSelect(Select):
	"""A select widget with courses related to a particular program as its choices"""
	def __init__(self, program=None, attrs=None):
		courses=program.classsubject_set.all()
		choices=[]
		for course in courses:
			course_title=course.title()
			choices.append((course_title, course_title))
		super(CourseSelect, self).__init__(attrs, choices)
		
class NameWidget(forms.MultiWidget):
	"""
	Custom widget for the 'Name' field
	"""
	def __init__(self, wclass='',*args, **kwargs):
		widgets=(forms.TextInput(attrs={'class':wclass}), forms.TextInput(attrs={'class':wclass}))
		super(NameWidget, self).__init__(widgets, *args, **kwargs)
		
	def decompress(self, value):
		"""
		'value' is a SortedDict
		"""
		
		if value:
			return value.values()
		return [None, None]
		
	def format_output(self, rendered_widgets):
		html_string=u'<table class="combo_field">'
		html_string+=u'<tr><td class="small_field">'+rendered_widgets[0]+u'</td><td class="small_field">'+rendered_widgets[1]+u'</td></tr>'
		html_string+=u'<tr class="subtext_row"><td>'+u'First'+u'</td><td>'+u'Last'+u'</td></tr>'
		html_string+=u'</table>'
		return html_string

class HiddenNameWidget(NameWidget):
	"""
	The hidden widget for the NameField class. Necessary to work with FormWizard
	"""
	is_hidden=True
	
	def __init__(self, *args, **kwargs):
		super(HiddenNameWidget, self).__init__(*args, **kwargs)
		for widget in self.widgets:
			widget.input_type='hidden'
			widget.is_hidden=True
			
	def format_output(self, rendered_widgets):
		return u''.join(rendered_widgets)		
	
class NameField(forms.MultiValueField):
	"""
	Custom field for the 'Name' field
	"""
	hidden_widget=HiddenNameWidget
	
	def __init__(self, *args, **kwargs):
		if 'name' in kwargs:
			self.name=kwargs.pop('name')
		widget_class=kwargs.pop('class')
		self.widget=NameWidget(wclass=widget_class)
		fields=(forms.CharField(), forms.CharField())
		super(NameField, self).__init__(fields, *args, **kwargs)
	
	def compress(self, value_list):
		compressed_value=SortedDict()
		if value_list:
			compressed_value[self.name+'_first_name']=value_list[0]
			compressed_value[self.name+'_last_name']=value_list[1]
		return compressed_value	
		
class AddressWidget(forms.MultiWidget):
	"""
	Custom widget for the 'Address' compound field type
	"""
	def __init__(self, wclass='', *args, **kwargs):
		widgets=(forms.TextInput(attrs={'size':'100', 'class':wclass}), forms.TextInput(attrs={'size':'30', 'class':wclass}), USStateSelect(attrs={'class':wclass}), forms.TextInput(attrs={'size':'5', 'class':wclass+' USZip'}))	
		super(AddressWidget, self).__init__(widgets, *args, **kwargs)
		
	def decompress(self, value):
		if value:
			return value.values()
		return [None, None, None, None]
		
	def format_output(self, rendered_widgets):
		html_string=u'<table class="combo_field">'
		html_string+=u'<tr><td>Street&nbsp;'+rendered_widgets[0]+'</td></tr>'
		html_string+=u'<tr><td>City&nbsp;'+rendered_widgets[1]+u'</td><td>State&nbsp;'+rendered_widgets[2]+u'</td></tr>'
		html_string+=u'<tr><td>Zip&nbsp;&nbsp;'+rendered_widgets[3]+u'</td></tr>'
		html_string+=u'</table>'
		return html_string
		
class HiddenAddressWidget(AddressWidget):
	"""
	The hidden widget for the AddressField class
	"""
	is_hidden=True
	
	def __init__(self, *args, **kwargs):
		super(HiddenAddressWidget, self).__init__(wclass='', *args, **kwargs)
		self.widgets=[forms.HiddenInput(), forms.HiddenInput(), forms.HiddenInput(), forms.HiddenInput()]
				
	def format_output(self, rendered_widgets):
		return u''.join(rendered_widgets)				
		
class AddressField(forms.MultiValueField):
	"""
	Custom field for the 'Address' combo field type
	"""
	hidden_widget=HiddenAddressWidget
	
	def __init__(self, *args, **kwargs):							
		if 'name' in kwargs:
			self.name=kwargs.pop('name')
		wclass=kwargs.pop('class')
		self.widget=AddressWidget(wclass=wclass)
		fields=(forms.CharField(max_length=100), forms.CharField(max_length=50), USStateField(), forms.CharField(max_length=5))
		super(AddressField, self).__init__(fields, *args, **kwargs)
		
	def compress(self, value_list):
		compressed_value=SortedDict()
		if value_list:
			compressed_value[self.name+'_street']=value_list[0]
			compressed_value[self.name+'_city']=value_list[1]
			compressed_value[self.name+'_state']=value_list[2]
			compressed_value[self.name+'_zip']=value_list[3]
		return compressed_value