" Survey models for Educational Studies Program. "

__author__    = "$LastChangedBy$"
__date__      = "$LastChangedDate$"
__rev__       = "$LastChangedRevision$"
__headurl__   = "$HeadURL$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from django.contrib import admin
from django.conf import settings
from esp.admin import admin_site
from esp.survey.models import Survey, SurveyResponse, QuestionType, Question, Answer
from esp.datatree.models import *

from copy import deepcopy
from StringIO import StringIO
import tempfile

def copy_surveys(modeladmin, request, queryset):
    survey_count = 0
    question_count = 0
    for survey in queryset:

        newsurvey, created = Survey.objects.get_or_create(name=survey.name + " (copy)", program=survey.program, category = survey.category)
        questions = survey.questions.order_by('id')
        if created: survey_count += 1

        for q in questions:
            # Create a new question for the new survey
            newq, created = Question.objects.get_or_create(survey=newsurvey, name=q.name, question_type=q.question_type, _param_values=q._param_values, per_class=q.per_class, seq=q.seq)
            newq.save()
            if created: question_count += 1

        newsurvey.save()
    modeladmin.message_user(request, "%s survey(s) copied, a total of %s question(s) copied" % (survey_count, question_count))

class SurveyAdmin(admin.ModelAdmin):
    actions = [ copy_surveys, ]
    list_filter = ('category',)
admin_site.register(Survey, SurveyAdmin)

class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('survey', 'time_filled')
    date_hierarchy = 'time_filled'
    list_filter = ('survey','time_filled')
admin_site.register(SurveyResponse, SurveyResponseAdmin)

class QuestionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', '_param_names', 'is_numeric', 'is_countable')
admin_site.register(QuestionType, QuestionTypeAdmin)

class QuestionAdmin(admin.ModelAdmin):
    list_display = ['seq', 'name', 'question_type', 'survey', 'per_class']
    list_display_links = ['name']
    list_filter = ['survey']
    search_filter = ('name',)
admin_site.register(Question, QuestionAdmin)

admin_site.register(Answer)
