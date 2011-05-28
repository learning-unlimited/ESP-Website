# Generates the custom models
from django.db import models
from customforms.models import *
from django.db import connection
from django.core.management import color
from django.db.backends.creation import BaseDatabaseCreation

def create_model(name, fields=None, app_label='', module='', options=None, admin_opts=None):
    """
    Create specified model
    """
    class Meta:
        # Using type('Meta', ...) gives a dictproxy error during model creation
        pass

    if app_label:
        # app_label must be set using the Meta inner class
        setattr(Meta, 'app_label', app_label)

    # Update Meta with any options that were provided
    if options is not None:
        for key, value in options.iteritems():
            setattr(Meta, key, value)

    # Set up a dictionary to simulate declarations within a class
    attrs = {'__module__': module, 'Meta': Meta}

    # Add in any fields that were provided
    if fields:
        attrs.update(fields)

    # Create the class, which automatically triggers ModelBase processing
    model = type(name, (models.Model,), attrs)

    # Create an Admin class if admin options were provided
    if admin_opts is not None:
        class Admin(admin.ModelAdmin):
            pass
        for key, value in admin_opts:
            setattr(Admin, key, value)
        admin.site.register(model, Admin)

    return model

def isReq(text):
	if text=='Y':
		return True
	else:
		return False	

def dynamic_model(form_id):
	# Figures out the fields for the model, and returns the dynamic model
	
	frm=Form.objects.get(id=form_id)
	fields={}
	questions=Question.objects.filter(form=frm).order_by('id').values('id','ques_type','required')
	for question in questions:
		required=isReq(question['required'])
		qtype=question['ques_type']
		qid=str(question['id'])
		if qtype=='textField':
			field=models.TextField(blank=not required,null=not required)
		elif qtype=='email':
			field=models.EmailField(max_length=75,blank=not required,null=not required)
		else:
			field=models.CharField(max_length=255,blank=not required,null=not required)
		fields['ques_'+qid]=field
	#generating the model
	dynamicModel=create_model('Response_form_'+str(form_id), fields,app_label='customforms',module='customforms.models')
	
	return dynamicModel	
	
def run_sql(model):
	#Runs the SQL to create the table and create indices
	
	style=color.no_style()
	cursor=connection.cursor()
	obj=BaseDatabaseCreation(connection)
	statements,pending = obj.sql_create_model(model,style)
	index_queries=obj.sql_indexes_for_model(model,style)
	for sql in statements:
		cursor.execute(sql)
	for query in index_queries:
		cursor.execute(query)	
	