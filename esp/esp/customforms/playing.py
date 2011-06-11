from form_utils.forms import BetterForm
from django import forms
from django.contrib.formtools.wizard import FormWizard
from django.shortcuts import redirect, render_to_response, HttpResponse

class MyForm1(BetterForm):
	one=forms.CharField()
	two=forms.CharField()
	three=forms.CharField()
	four=forms.CharField()
	five=forms.CharField()
	
	class Meta:
		fieldsets=(('first', {'fields':['one', 'two', 'three']}), 
					('second', {'fields':['four', 'five']}))

class MyForm2(BetterForm):
	one=forms.CharField()
	two=forms.CharField()
	three=forms.CharField()
	four=forms.CharField()
	five=forms.CharField()
	
	class Meta:
		fieldsets=(('first', {'fields':['one', 'two',]}), 
					('second', {'fields':['four', 'five']}))
					
class Combo(FormWizard):
	
	def done(self, request, form_list):
		return HttpResponse('Done')
	
	def get_template(self, step):
		return 'customforms/playing.html'	 											