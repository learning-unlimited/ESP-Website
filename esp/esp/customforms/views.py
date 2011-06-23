from django.db import transaction
from django.shortcuts import redirect, render_to_response, HttpResponse
from django.http import Http404,HttpResponseRedirect
from django.template import RequestContext
from django.db import connection
from django.utils import simplejson as json
from customforms.models import *
#from customforms.useful import *
#from customforms.backups import *
from esp.program.models import Program
from esp.customforms.DynamicModel import DynamicModelHandler as DMH
from esp.customforms.DynamicForm import FormHandler

def landing(request):
	if request.user.is_authenticated():
		form_list=Form.objects.filter(created_by=request.user)
		return render_to_response('customforms/landing.html',{'form_list':form_list})
	else: 
		return HttpResponseRedirect('/')	

def formBuilder(request):
	if request.user.is_authenticated():
		prog_list=Program.objects.all()
		return render_to_response('customforms/index.html',{'prog_list':prog_list})
	else: 
		return HttpResponseRedirect('/')	

def is_required(text):
	#returns True if the field is required, else False
	if(text=='true'):
		return True
	else:
		return False	

@transaction.commit_on_success
def onSubmit(request):
	#Stores form metadata in the database.
	
	if request.is_ajax():
		if request.method == 'POST':
			metadata=json.loads(request.raw_post_data)
			
			fields=[]
			
		#Creating form
		form=Form.objects.create(title=metadata['title'], description=metadata['desc'], created_by=request.user, link_type=metadata['link_type'], link_id=int(metadata['link_id']), anonymous=is_required(metadata['anonymous']))
		
		#Inserting pages
		for i,page in enumerate(metadata['pages']):
			new_page=Page.objects.create(form=form, seq=i)
			
			#inserting sections
			for section in page['sections']:
				new_section=Section.objects.create(page=new_page, title=section['data']['question_text'], description=section['data']['help_text'], seq=int(section['data']['seq']))
				
				#inserting fields
				for field in section['fields']:
					new_field=Field.objects.create(form=form, section=new_section, field_type=field['data']['field_type'], seq=int(field['data']['seq']), label=field['data']['question_text'], help_text=field['data']['help_text'], required=is_required(field['data']['required']))
					fields.append( (new_field.id, new_field.field_type) ) 
					
					#inserting other attributes, if any
					for attr in field['data']['attrs']:
						new_attr=Attribute.objects.create(field=new_field, attr_type=attr.keys()[0], value=attr.values()[0])
						
		dynH=DMH(form=form, fields=fields)
		dynH.createTable()				
							
		return HttpResponse('OK')
		
def viewForm(request, form_id):
	"""Form viewing and submission"""
	try:
		form_id=int(form_id)
	except ValueError:
		raise Http404
		
	form=Form.objects.get(pk=form_id)
	fh=FormHandler(form=form, user=request.user)
	wizard=fh.getWizard()
	extra_context={'form_title':form.title, 'form_description':form.description}
	return wizard(request, extra_context=extra_context)	

def success(request):
	"""
	Successful form submission
	"""
	return render_to_response('customforms/success.html',{})

def viewResponse(request, form_id):
	"""
	Viewing response data
	"""
	if request.user.is_authenticated:
		try:
			form_id=int(form_id)
		except ValueError:
			raise Http404
		form=Form.objects.get(id=form_id)
		return render_to_response('customforms/view_results.html', {'form':form})
	else:
		return HttpResponseRedirect('/')
		
def getData(request):
	"""
	Returns response data via Ajax
	"""
	if request.is_ajax():
		if request.method=='GET':
			try:
				form_id=int(request.GET['form_id'])
			except ValueError:
				raise HttpResponse(status=400)
			form=Form.objects.get(pk=form_id)	
			fh=FormHandler(form=form)
			resp_data=json.dumps(fh.getResponseData(form))
			return HttpResponse(resp_data)
	else:
		return HttpResponse(status=400)