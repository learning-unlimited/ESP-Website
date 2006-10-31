from django.db import models
from django.contrib.auth.models import User
from django.template import Context, loader

# Create your models here.

class Survey(models.Model):
    title = models.TextField()
    create_time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, blank=True, null=True)

    def __str__(self):
        return "Survey: " + self.title

    def to_html(self):
        return loader.get_template('poll/survey').render(Context({'survey': self}))

    class Admin:
        pass

class SurveyResponse(models.Model):
    user = models.ForeignKey(User)
    create_time = models.DateTimeField(auto_now_add=True)
    source_survey = models.ForeignKey(Survey)

    def __str__(self):
        return "SurveyResponse: " + self.source_survey.title + " (" + str(self.create_time) + ")"

    class Admin:
        pass

class Question(models.Model):
    question = models.TextField()
    q_type = models.SlugField() # The HTML type of the field to be used to render this question
    survey = models.ForeignKey(Survey)

    def __str__(self):
        return "Question: " + self.question

    def to_html(self):
        return loader.get_template('poll/question').render(Context({'question': self}))

    class Admin:
        pass

class QField(models.Model):
    label = models.TextField(blank=True)
    val = models.IntegerField(blank=True, null=True)
    question = models.ForeignKey(Question)
    wants_text = models.BooleanField(default=False)

    def __str__(self):
        return "QField: " + self.label

    def to_html(self):
        return loader.get_template('poll/qfield').render(Context({'qfield': self}))
    
    class Admin:
        pass

class QResponse(models.Model):
    qfield = models.ForeignKey(QField)
    response_text = models.TextField(blank=True)
    response = models.ForeignKey(SurveyResponse)

    def __str__(self):
        return "QResponse to " + self.qfield.label + " (" + self.response_text + ")"

    class Admin:
        pass
