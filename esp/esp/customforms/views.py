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

@transaction.commit_on_success		
def onModify(request):
	"""
	Handles form modifications
	"""
	if request.is_ajax():
		if request.method=='POST':
			metadata=json.loads(request.raw_post_data)
			form=Form.objects.filter(id=int(metadata['form_id']))
			dmh=DMH(form=form[0])
			form.update(title=metadata['title'], description=metadata['desc'], link_type=metadata['link_type'], link_id=int(metadata['link_id']), anonymous=metadata['anonymous'])
			curr_keys={'pages':[], 'sections':[], 'fields':[]}
			old_pages=Page.objects.filter(form=form[0])
			old_sections=Section.objects.filter(page__in=old_pages)	
			old_fields=Field.objects.filter(form=form[0])
			for page in metadata['pages']:
				if page['parent_id']==-1:
					#New page
					curr_page=Page.objects.create(form=form[0], seq=int(page['seq']))
				else:
					cp=old_pages.filter(id=int(page['parent_id']))
					cp.update(form=form[0], seq=page['seq'])
					curr_page=cp[0]
				curr_keys['pages'].append(curr_page.id)
				for section in page['sections']:
					if section['data']['parent_id']==-1:
						#New Section
						curr_sect=Section.objects.create(page=curr_page, title=section['data']['question_text'], description=section['data']['help_text'], seq=int(section['data']['seq']))
					else:
						cs=old_sections.filter(id=section['data']['parent_id'])
						cs.update(page=curr_page, title=section['data']['question_text'], description=section['data']['help_text'], seq=int(section['data']['seq']))
						curr_sect=cs[0]
					curr_keys['sections'].append(curr_sect.id)
					for field in section['fields']:
						if field['data']['parent_id']==-1:
							#New field
							curr_field=Field.objects.create(form=form[0], section=curr_sect, field_type=field['data']['field_type'], seq=int(field['data']['seq']), label=field['data']['question_text'], help_text=field['data']['help_text'], required=field['data']['required'])
							dmh.addField(curr_field)
							for atype, aval in field['data']['attrs'].items():
								Attribute.objects.create(field=curr_field, attr_type=atype, value=aval)
						else:
							curr_field=old_fields.filter(id=int(field['data']['parent_id']))
							curr_field.update(form=form[0], section=curr_sect, field_type=field['data']['field_type'], seq=int(field['data']['seq']), label=field['data']['question_text'], help_text=field['data']['help_text'], required=field['data']['required'])
							for atype, aval in field['data']['attrs'].items():
								Attribute.objects.filter(field=curr_field[0]).update(field=curr_field[0], attr_type=atype, value=aval)
							curr_field=curr_field[0]	
						curr_keys['fields'].append(curr_field.id)
						
			del_fields=old_fields.exclude(id__in=curr_keys['fields'])
			for df in del_fields:
				dmh.removeField(df)
				df.delete()
				
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
	
	
			