from django import forms

def isRequired(text):
	#Returns True if the field is required, False otherwise
	
	if text=='Y':
		return True
	else:
		return False

class CustomForm(forms.Form):
	
		
	
	def __init__(self,*args,**kwargs):
		#The init method allows us to create forms dynamically
		
		properties=kwargs.pop('properties')
		super(CustomForm,self).__init__(*args,**kwargs)
		
		for prop in properties:
			ques_id=prop['id']
			if prop['ques_type']=='name':
				self.fields[str(ques_id)] = forms.CharField(label=prop['ques'],required=isRequired(prop['required']))
			elif prop['ques_type']=='email':
				self.fields[str(ques_id)]=forms.EmailField(label=prop['ques'],required=isRequired(prop['required']))
			elif prop['ques_type']=='textField':
				self.fields[str(ques_id)]=forms.CharField(label=prop['ques'],required=isRequired(prop['required']))
			elif prop['ques_type']=='phone':
				self.fields[str(ques_id)]=forms.IntegerField(label=prop['ques'],required=isRequired(prop['required']))
			elif prop['ques_type']=='radio':
				self.fields[str(ques_id)]=forms.ChoiceField(label=prop['ques'],required=isRequired(prop['required']),widget=forms.RadioSelect, choices=prop['opts'])
			elif prop['ques_type']=='gender':
				self.fields[str(ques_id)]=forms.ChoiceField(label=prop['ques'],required=isRequired(prop['required']),widget=forms.RadioSelect, choices=[['Male','Male'],['Female','Female']])
	