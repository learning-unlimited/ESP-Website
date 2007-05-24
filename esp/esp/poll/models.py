
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django.db import models
from django.contrib.auth.models import User
from django.template import Context, loader
from esp.datatree.models import DataTree
import datetime
from esp.db.fields import AjaxForeignKey

# Create your models here.

class Survey(models.Model):
    path = AjaxForeignKey(DataTree)
    name = models.SlugField()
    title = models.TextField()
    create_date = models.DateTimeField(default=datetime.datetime.now,
                                       editable=False)
    author = AjaxForeignKey(User, blank=True, null=True)

    def __str__(self):
        return "Survey: " + self.title

    def html(self, postback="index.poll"):
        return loader.get_template('poll/survey').render(Context({'survey': self, 'postback': postback}))

    class Admin:
        pass

class SurveyResponse(models.Model):
    author = AjaxForeignKey(User)
    create_date = models.DateTimeField(auto_now_add=True)
    source_survey = models.ForeignKey(Survey)

    def __str__(self):
        return "SurveyResponse: " + self.source_survey.title + " (" + str(self.create_time) + ")"

    class Admin:
        pass

class Question(models.Model):
    question = models.TextField()
    q_type = models.SlugField() # The HTML type of the field to be used to render this question
    survey = models.ForeignKey(Survey)
    create_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Question: " + self.question

    def html(self):
        return loader.get_template('poll/question').render(Context({'question': self}))

    class Admin:
        pass

class QField(models.Model):
    label = models.TextField(blank=True)
    val = models.IntegerField(blank=True, null=True)
    question = models.ForeignKey(Question)
    wants_text = models.BooleanField(default=False)
    create_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "QField: " + self.label

    def html(self):
        return loader.get_template('poll/qfield').render(Context({'qfield': self}))
    
    class Admin:
        pass

class QResponse(models.Model):
    qfield = models.ForeignKey(QField)
    response_text = models.TextField(blank=True)
    response = models.ForeignKey(SurveyResponse)
    create_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "QResponse to " + self.qfield.label + " (" + self.response_text + ")"

    class Admin:
        pass

