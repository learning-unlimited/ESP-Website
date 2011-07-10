from django.db import transaction
from django.shortcuts import redirect, render_to_response, HttpResponse
from django.http import Http404,HttpResponseRedirect
from django.template import RequestContext
from django.db import connection
from django.utils import simplejson as json
from customforms.models import *
from esp.program.models import Program
from esp.customforms.DynamicModel import DynamicModelHandler as DMH
from esp.customforms.DynamicForm import FormHandler

from esp.users.models import ESPUser
from esp.middleware import ESPError

def landing(request):
	if request.user.is_authenticated():
		forms=Form.objects.filter(created_by=request.user)
		return render_to_response("customforms/landing.html", {'form_list':forms}, context_instance=RequestContext(request))
	return HttpResponseRedirect('/')	

def formBuilder(request):
	if request.user.is_authenticated():
		prog_list=Program.objects.all()
		form_list=Form.objects.filter(created_by=request.user)
		return render_to_response('customforms/index.html',{'prog_list':prog_list, 'form_list':form_list}) 
	return HttpResponseRedirect('/')	

@transaction.commit_on_success
def onSubmit(request):
	#Stores form metadata in the database.
	
	if request.is_ajax():
		if request.method == 'POST':
			metadata=json.loads(request.raw_post_data)
			
			fields=[]
			
		#Creating form
		form=Form.objects.create(title=metadata['title'], description=metadata['desc'], created_by=request.user, link_type=metadata['link_type'], link_id=int(metadata['link_id']), anonymous=metadata['anonymous'])
		
		#Inserting pages
		for page in metadata['pages']:
			new_page=Page.objects.create(form=form, seq=int(page['seq']))
			
			#inserting sections
			for section in page['sections']:
				new_section=Section.objects.create(page=new_page, title=section['data']['question_text'], description=section['data']['help_text'], seq=int(section['data']['seq']))
				
				#inserting fields
				for field in section['fields']:
					new_field=Field.objects.create(form=form, section=new_section, field_type=field['data']['field_type'], seq=int(field['data']['seq']), label=field['data']['question_text'], help_text=field['data']['help_text'], required=field['data']['required'])
					fields.append( (new_field.id, new_field.field_type) ) 
					
					#inserting other attributes, if any
					for atype, aval in field['data']['attrs'].items():
						new_attr=Attribute.objects.create(field=new_field, attr_type=atype, value=aval)
						
		dynH=DMH(form=form, fields=fields)
		dynH.createTable()				
							
		return HttpResponse('OK')

def get_or_create_altered_obj(model, initial_id, **attrs):
	if model.objects.filter(id=initial_id).exists():
		obj = model.objects.get(id=initial_id)
		obj.__dict__.update(attrs)
		obj.save()
		created = False
	else:
		obj = model.objects.create(**attrs)
		created = True
	return (obj, created)
	
def get_new_or_altered_obj(*args, **kwargs):
	return get_or_create_altered_obj(*args, **kwargs)[0]

@transaction.commit_on_success		
def onModify(request):
	"""
	Handles form modifications
	"""
	if request.is_ajax():
		if request.method=='POST':
			metadata=json.loads(request.raw_post_data)
			try:
				form=Form.objects.get(id=int(metadata['form_id']))
			except:
				raise ESPError(False), 'Form %s not found' % metadata['form_id']
			dmh=DMH(form=form)
			form.__dict__.update(title=metadata['title'], description=metadata['desc'], link_type=metadata['link_type'], link_id=int(metadata['link_id']), anonymous=metadata['anonymous'])
			form.save()
			curr_keys={'pages':[], 'sections':[], 'fields':[]}
			old_pages=Page.objects.filter(form=form)
			old_sections=Section.objects.filter(page__in=old_pages)	
			old_fields=Field.objects.filter(form=form)
			for page in metadata['pages']:
				curr_page = get_new_or_altered_obj(Page, page['parent_id'], form=form, seq=int(page['seq']))
				curr_keys['pages'].append(curr_page.id)
				for section in page['sections']:
					curr_sect = get_new_or_altered_obj(Section, section['data']['parent_id'], page=curr_page, title=section['data']['question_text'], description=section['data']['help_text'], seq=int(section['data']['seq']))
					curr_keys['sections'].append(curr_sect.id)
					for field in section['fields']:
						(curr_field, field_created) = get_or_create_altered_obj(Field, field['data']['parent_id'], form=form, section=curr_sect, field_type=field['data']['field_type'], seq=int(field['data']['seq']), label=field['data']['question_text'], help_text=field['data']['help_text'], required=field['data']['required'])
						if field_created:
							dmh.addField(curr_field)
						else:
							dmh.updateField(curr_field)
						for atype, aval in field['data']['attrs'].items():
							curr_field.set_attribute(atype, aval)
						curr_keys['fields'].append(curr_field.id)
						
			del_fields=old_fields.exclude(id__in=curr_keys['fields'])
			for df in del_fields:
				dmh.removeField(df)
			del_fields.delete()
				
			old_sections.exclude(id__in=curr_keys['sections']).delete()
			old_pages.exclude(id__in=curr_keys['pages']).delete()				
			
			#Removing obsolete items
			"""for f in to_delete['fields']:
				dmh.removeField(f)
				f.delete()
				
			for s in to_delete['sections']:
				s.delete()
				
			for p in to_delete['pages']:
				p.delete()"""		
				
			"""for old_page in old_pages:
				old_sections=Section.objects.filter(page=old_page)
				for old_section in old_sections:
					old_fields=Field.objects.filter(section=old_section)
					for old_field in old_fields:
						if old_field.id not in curr_keys['fields']:
							dmh.removeField(old_field)
							old_field.delete()
					if old_section.id not in curr_keys['sections']: old_section.delete()
				if old_page.id not in curr_keys['pages']: old_page.delete()"""
			
			return HttpResponse('OK')									 			
					
		
def viewForm(request, form_id):
	"""Form viewing and submission"""
	try:
		form_id=int(form_id)
	except ValueError:
		raise Http404
		
	form=Form.objects.get(pk=form_id)
	if (not form.anonymous) and not request.user.is_authenticated():
		return HttpResponseRedirect('/')
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
				return HttpResponse(status=400)
			form=Form.objects.get(pk=form_id)	
			fh=FormHandler(form=form)
			resp_data=json.dumps(fh.getResponseData(form))
			return HttpResponse(resp_data)
	return HttpResponse(status=400)
		
def getRebuildData(request):
	"""
	Returns form metadata for rebuilding via AJAX
	"""
	if request.is_ajax():
		if request.method=='GET':
			try:
				form_id=int(request.GET['form_id'])
			except ValueError:
				return HttpResponse(status=400)
			form=Form.objects.get(pk=form_id)
			fh=FormHandler(form=form)
			metadata=json.dumps(fh.rebuildData())
			return HttpResponse(metadata)
	return HttpResponse(status=400)						
		
def test():
	f=Form.objects.get(pk=16)
	from esp.customforms.DynamicForm import rd
	dyn=DMH(form=f).createDynModel()
	rd.depend_on_model(lambda:dyn)
	rd.run_all_delayed()
	data1=rd(dyn,f)
	user=ESPUser.objects.get(pk=1)
	dyn.objects.create(user=user, question_83='yyy')
	data2=rd(dyn,f)
	return {'first':data1, 'second':data2}
	
	
			