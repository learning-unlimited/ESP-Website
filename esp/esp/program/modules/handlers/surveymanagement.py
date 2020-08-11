
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_grade, main_call, aux_call
from esp.program.modules import module_ext
from esp.program.models import ClassSubject, ClassSection
from esp.utils.web import render_to_response
from esp.users.models    import ESPUser
from django.db.models.query   import Q
from esp.middleware     import ESPError
from esp.survey.models  import QuestionType, Question, Answer, SurveyResponse, Survey
from esp.survey.views   import survey_view, survey_review, survey_graphical, survey_review_single, top_classes, survey_dump
from esp.program.modules.forms.surveys import SurveyForm, QuestionForm, SurveyImportForm

from collections import OrderedDict
import json

class SurveyManagement(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Survey Management",
            "link_title": "Surveys",
            "module_type": "manage",
            "seq": 25,
            'choosable': 1,
            }

    def isStep(self):
        return False

    @needs_admin
    def survey_manage(self, request, tl, one, two, module, extra, prog):
        context = {'program': prog}
        # Make some dummy data for survey questions that need it
        classes = [ClassSubject(id = i, title="Test %s" %i, parent_program = prog, category = prog.class_categories.all()[0],
                   grade_min = prog.grade_min, grade_max = prog.grade_max) for i in range(1,4)]
        context['classes'] = classes
        context['section'] = ClassSection(parent_class=classes[0])
        context['question_types'] = json.dumps({str(qt.id): qt.param_names for qt in QuestionType.objects.all()})
        if request.GET:
            obj = request.GET.get("obj", None)
            op = request.GET.get("op", None)
            id = request.GET.get("id", None) or request.POST.get("survey_id", None) or request.POST.get("question_id", None)
            if obj == "survey":
                context['open_section'] = 'survey'
                survey = None
                surveys = Survey.objects.filter(id = id)
                if request.POST and not op:
                    if len(surveys) == 1:
                        # submitted question form to edit an existing question
                        form = SurveyForm(request.POST, instance = surveys[0])
                        form.id = id
                    else:
                        # submitted question form to create new question
                        form = SurveyForm(request.POST)
                    if form.is_valid():
                        form.save(program = prog)
                    else:
                        context['survey_form'] = form
                elif len(surveys) == 1:
                    survey = surveys[0]
                    if op == "edit":
                        # clicked edit link
                        form = SurveyForm(instance = survey)
                        form.id = id
                        context['survey_form'] = form
                    elif op == "delete":
                        if 'delete_confirm' in request.POST and request.POST['delete_confirm'] == 'yes':
                            # confirmed deletion
                            # delete questions
                            survey.questions.all().delete()
                            # delete survey
                            survey.delete()
                        else:
                            # clicked delete link
                            context['survey'] = survey
                            context['questions'] = survey.questions.order_by('seq')
                            return render_to_response('program/modules/surveymanagement/survey_delete.html', request, context)
                    elif op == "import":
                        if 'import_confirm' in request.POST and request.POST['import_confirm'] == 'yes':
                            # confirmed import
                            to_import = request.POST.getlist('to_import')

                            # Create new survey
                            newsurvey, created = Survey.objects.get_or_create(name=survey.name, program=prog, category=survey.category)

                            # Create new questions for the new survey, if they were selected
                            questions = survey.questions.order_by('id')
                            for q in questions:
                                if str(q.id) in to_import:
                                    Question.objects.get_or_create(survey=newsurvey, name=q.name, question_type=q.question_type, _param_values=q._param_values, per_class=q.per_class, seq=q.seq)
                        else:
                            # submitted import form
                            context['survey'] = survey
                            context['questions'] = survey.questions.order_by('seq')
                            return render_to_response('program/modules/surveymanagement/import.html', request, context)
            elif obj == "question":
                context['open_section'] = 'question'
                question = None
                questions = Question.objects.filter(id = id)
                if request.POST and not op:
                    if len(questions) == 1:
                        # submitted question form to edit an existing question
                        form = QuestionForm(request.POST, instance = questions[0], cur_prog = prog)
                        form.id = id
                    else:
                        # submitted question form to create new question
                        form = QuestionForm(request.POST, cur_prog = prog)
                    if form.is_valid():
                        form.save()
                    else:
                        context['question_form'] = form
                elif len(questions) == 1:
                    question = questions[0]
                    if op == "edit":
                        # clicked edit link
                        form = QuestionForm(instance = question, cur_prog = prog)
                        form.id = id
                        context['question_form'] = form
                    elif op == "delete":
                        if 'delete_confirm' in request.POST and request.POST['delete_confirm'] == 'yes':
                            # confirmed deletion
                            question.delete()
                        else:
                            # clicked delete link
                            context['question'] = question
                            return render_to_response('program/modules/surveymanagement/question_delete.html', request, context)
        if 'survey_form' not in context:
            context['survey_form'] = SurveyForm()
        if 'question_form' not in context:
            context['question_form'] = QuestionForm(cur_prog = prog)
        if 'import_survey_form' not in context:
            context['import_survey_form'] = SurveyImportForm(cur_prog = prog)
        context['surveys'] = Survey.objects.filter(program = prog)
        context['questions'] = Question.objects.filter(survey__program = prog).order_by('survey__category', 'survey', 'per_class', 'seq')

        return render_to_response('program/modules/surveymanagement/manage.html', request, context)

    @main_call
    @needs_admin
    def surveys(self, request, tl, one, two, module, extra, prog):
        if extra is None or extra == '':
            surveys = prog.getSurveys()
            counts = {}
            for s in surveys:
                if s.category not in counts:
                    counts[s.category] = 1
                else:
                    counts[s.category] += 1
            return render_to_response('program/modules/surveymanagement/main.html', request, {'program': prog, 'surveys': surveys, 'counts': counts})
        elif extra == 'manage':
            return self.survey_manage(request, tl, one, two, module, extra, prog)
        elif extra == 'review':
            return survey_review(request, tl, one, two)
        elif extra == 'dump':
            return survey_dump(request, tl, one, two)
        elif extra == 'review_pdf':
            return survey_graphical(request, tl, one, two)
        elif extra == 'review_single':
            return survey_review_single(request, tl, one, two)
        elif extra == 'top_classes':
            return top_classes(request, tl, one, two)

    survey = surveys

    class Meta:
        proxy = True
        app_label = 'modules'
