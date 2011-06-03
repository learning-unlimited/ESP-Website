from django.db import models
from esp.users.models import ESPUser
from program.models import Program

"""class Form(models.Model):
	title=models.CharField(max_length=40)
	description=models.CharField(max_length=140)
	program=models.ForeignKey(Program)
	date_created=models.DateField(auto_now_add=True)
	created_by=models.ForeignKey(ESPUser)
	
class Page(models.Model):
	form=models.ForeignKey(Form)
	
class Section(models.Model):
	page=models.ForeignKey(Page)
	title=models.CharField(max_length=40)
	description=models.CharField(max_length=40)
	seq=models.IntegerField()

class Field(models.Model):
	section=models.ForeignKey(Section)
	seq=models.IntegerField()
	label=models.CharField(max_length=200)
	help_text=models.CharField(max_length=200)
	required=models.BooleanField()
	
class Attribute(models.Model):
	field=models.ForeignKey(Field)
	attr_type=models.CharField(max_length=15)
	value=models.CharField(max_length=40)"""				