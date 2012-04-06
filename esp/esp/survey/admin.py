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
  Email: web-team@lists.learningu.org
"""

from django.contrib import admin
from django.conf import settings
from esp.admin import admin_site
from esp.survey.models import Survey, SurveyResponse, QuestionType, Question, Answer
from esp.datatree.models import *

from copy import deepcopy
from StringIO import StringIO
import tempfile

def save_survey(survey, outfile):
    anchor_uri = survey.anchor.uri
    anchor_uri_len = len(anchor_uri)

    questions = survey.questions.order_by('id')

    for q in questions:
        str_fragments = []
        str_fragments.append('%d' % q.seq)
        str_fragments.append(q.anchor.uri[anchor_uri_len:])
        str_fragments.append(q._param_values)
        str_fragments.append('%d' % q.question_type_id)
        str_fragments.append(q.name)
        outfile.write('":"'.join(str_fragments))
        outfile.write('\n.\n')

def load_survey(survey_anchor, survey_name, category, infile):
    # create survey
    survey, created = Survey.objects.get_or_create(name=survey_name, anchor=survey_anchor, category=category)
    survey.save()
    
    auri = survey_anchor.uri

    data = infile.read()
    entries = data.split('\n.\n')[:-1]
    for entry in entries:
        qlist = entry.split('":"')
        seq = int(qlist[0])
        anchor = DataTree.get_by_uri(auri + qlist[1])
        pv = qlist[2]
        qt = QuestionType.objects.get(id=qlist[3])
        name = qlist[4]
        q, c = Question.objects.get_or_create(survey=survey, name=name, question_type=qt, _param_values=pv, anchor=anchor, seq=seq)
        q.save()

def copy_surveys(modeladmin, request, queryset):
    for survey in queryset:
        # Use a memory file instead of a real one, because it will be faster. This assumes
        # the survey will not be unreasonably large.
        tmp_mem_file = StringIO()
        save_survey(survey, tmp_mem_file)
        tmp_mem_file.seek(0)
        load_survey(survey.anchor, survey.name + " (copy)", survey.category, tmp_mem_file)
        tmp_mem_file.close()

class SurveyAdmin(admin.ModelAdmin):
    actions = [ copy_surveys, ]

    def save_model(self, request, obj, form, change):
        # Ensure that our questions always match up with the form
        for q in obj.questions.all():
            q.anchor = obj.anchor
            q.save()
        obj.save()

admin_site.register(Survey, SurveyAdmin)

class SurveyResponseAdmin(admin.ModelAdmin):
    pass
admin_site.register(SurveyResponse, SurveyResponseAdmin)
    
admin_site.register(QuestionType)

class QuestionAdmin(admin.ModelAdmin):
    list_display = ['seq', 'name', 'question_type', 'survey']
    list_display_links = ['name']
    list_filter = ['survey']
admin_site.register(Question, QuestionAdmin)

admin_site.register(Answer)
