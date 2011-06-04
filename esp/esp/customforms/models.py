from django.db import models
#from esp.users.models import ESPUser
from django.contrib.auth.models import User
from esp.program.models import Program

class Form(models.Model):
	title=models.CharField(max_length=40, blank=True)
	description=models.CharField(max_length=140, blank=True)
	date_created=models.DateField(auto_now_add=True)
	created_by=models.ForeignKey(User)
	link_type=models.CharField(max_length=10, choices=( ('program', 'Program'), ('course', 'Course'), ('none','None') ), blank=True)
	link_id=models.IntegerField(default=-1)
	
class Page(models.Model):
	form=models.ForeignKey(Form)
	seq=models.IntegerField(default=-1)
	
class Section(models.Model):
	page=models.ForeignKey(Page)
	title=models.CharField(max_length=40)
	description=models.CharField(max_length=140, blank=True)
	seq=models.IntegerField()

class Field(models.Model):
	section=models.ForeignKey(Section)
	field_type=models.CharField(max_length=20)
	seq=models.IntegerField()
	label=models.CharField(max_length=200)
	help_text=models.CharField(max_length=200, blank=True)
	required=models.BooleanField()
	
class Attribute(models.Model):
	field=models.ForeignKey(Field)
	attr_type=models.CharField(max_length=15)
	value=models.CharField(max_length=40)				
