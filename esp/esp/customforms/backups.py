import os
import tarfile
from django.core import serializers
import json
from customforms.models import *
from customforms.useful import *

"""
#Directories to work in
temp_dir=os.path.join(os.path.dirname(__file__), '../form_backups/temp')
backup_dir=os.path.join(os.path.dirname(__file__), '../form_backups')

#Stuff to archive
toArchive=['questions','options','responses']

def dumpToFile(form):
	
	dumps={}
	
	#getting all questions
	dumps['questions']=Question.objects.filter(form=form).order_by('id')
	
	#getting all options
	dumps['options']=Option.objects.filter(form=form)
	
	#getting all responses
	dyn_model=dynamic_model(form.id)
	dumps['responses']=dyn_model.objects.all()
	
	#Dumping questions, options and responses in their respective files
	JSONSerializer=serializers.get_serializer('json')
	json_serializer=JSONSerializer()
	
	for dump in dumps:
		out=open(os.path.join(temp_dir,str(form.id) + '_' + dump),'w')
		json_serializer.serialize(dumps[dump],stream=out)
		out.close()
	
	#tarring and gzipping files, moving to main backup directory
	os.chdir(temp_dir)
	
	t=tarfile.open(os.path.join(backup_dir, str(form.id)+'.tar.gz'), 'w:gz')
	
	for obj in toArchive:
		t.add(str(form.id) +'_'+obj)
		
	t.close()
	
	#Deleting temporary files
	for obj in toArchive:
		os.remove(str(form.id)+'_'+obj)
		

def restoreFromFile(form):
	
	#Decompressing the tar.gz file into the temporary folder
	os.chdir(temp_dir)
	t=tarfile.open(os.path.join(backup_dir, str(form.id)+'.tar.gz'))
	t.extractall()
	t.close()
	
	#Restoring everything except reponses
	for tAr in toArchive:
		if tAr=='responses':
			continue
		backFile=open(str(form.id)+'_'+tAr,'r')
		for obj in serializers.deserialize('json',backFile):
			obj.save()
			
	#Restoring responses table
	dynModel=dynamic_model(form.id)
	run_sql(dynModel)
	backFile=open(str(form.id)+'_responses','r')
	for row in json.load(backFile):
		dynModel.objects.create(**row['fields'])
	backFile.close()	
	#deleting temporary files
	for obj in toArchive:
		os.remove(str(form.id)+'_'+obj)
		
	#deleting archived data for this form
	os.remove(os.path.join(backup_dir,str(form.id)+'.tar.gz'))
"""	
	
