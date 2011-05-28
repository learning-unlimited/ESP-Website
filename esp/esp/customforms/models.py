from django.db import models

class MyUser(models.Model):
	name=models.CharField(max_length=15, default="User")

class Form(models.Model):
	title=models.CharField(max_length=30,default="Form")
	active=models.IntegerField(max_length=2,default=1)
	
class Question(models.Model):
	form=models.ForeignKey(Form)
	question=models.CharField(max_length=60)
	ques_type=models.CharField(max_length=15)
	required=models.CharField(max_length=2)
	
class Option(models.Model):
	#Stores options for a particular multiple-choice type question
	
	form=models.ForeignKey(Form)
	question=models.ForeignKey(Question)
	opt=models.CharField(max_length=30)
	
	
		
class Responses(models.Model):
	#The static table for responses. NOT being used currently.
	
	question=models.ForeignKey(Question)
	resp=models.CharField(max_length=50,null=True,blank=True)	
	form=models.ForeignKey(Form)
	myuser=models.ForeignKey(MyUser)