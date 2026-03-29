
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.program.models import ClassSubject, ClassSection
from esp.utils.web import render_to_response
from esp.survey.models  import QuestionType, Question, Survey
from esp.survey.views   import survey_review, survey_graphical, survey_review_single, top_classes, survey_dump
from esp.program.modules.forms.surveys import SurveyForm, QuestionForm, SurveyImportForm, CSVQuestionImportForm, parse_csv

import csv\nimport json

from django.http import HttpResponse

class SurveyManagement(ProgramModuleObj):
    doc = """Manage the post-program/class surveys that are served to students/teachers during registration."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Survey Management",
            "link_title": "Surveys",
            "module_type": "manage",
            "seq": 25,
            'choosable': 1,
            }

    @needs_admin
    def survey_manage(self, request, tl, one, two, module, extra, prog, extra_context=None):
        context = {'program': prog}
        # Make some dummy data for survey questions that need it
        classes = [ClassSubject(id = i, title="Test %s" %i, parent_program = prog, category = prog.class_categories.all()[0],
                   grade_min = prog.grade_min, grade_max = prog.grade_max) for i in range(1, 4)]
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
        if 'csv_import_form' not in context:
            context['csv_import_form'] = CSVQuestionImportForm(cur_prog = prog)
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
        elif extra == 'csv_template':
            return self.csv_template_download(request, tl, one, two, module, extra, prog)
        elif extra == 'csv_import':
            return self.csv_import(request, tl, one, two, module, extra, prog)

    @needs_admin
    def csv_template_download(self, request, tl, one, two, module, extra, prog):
        """Generate and return a CSV template file with headers and example rows."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="survey_questions_template.csv"'

        writer = csv.writer(response)
        writer.writerow(['question_text', 'question_type', 'per_class', 'seq', 'param_values'])

        # Add example rows using actual QuestionType names from the database
        question_types = list(QuestionType.objects.values_list('name', flat=True)[:3])
        examples = [
            ('How would you rate this program?', question_types[0] if len(question_types) > 0 else 'yes-no response', 'false', '1', ''),
            ('Rate your class experience', question_types[1] if len(question_types) > 1 else 'numeric rating', 'true', '2', '5|Low|Medium|High'),
            ('Any additional comments?', question_types[0] if len(question_types) > 0 else 'yes-no response', 'false', '3', ''),
        ]
        for example in examples:
            writer.writerow(example)

        return response

    @needs_admin
    def csv_import(self, request, tl, one, two, module, extra, prog):
        """Handle CSV file upload, preview, and import of survey questions."""
        context = {'program': prog}

        if request.method == 'POST' and 'import_confirm' in request.POST:
            # Step 2: Confirmed import — create Question objects
            survey_id_raw = request.POST.get('survey_id')
            try:
                survey_id = int(survey_id_raw)
            except (TypeError, ValueError):
                from esp.middleware import ESPError
                raise ESPError('Invalid survey selection for import.', log=False)

            try:
                survey = Survey.objects.get(id=survey_id, program=prog)
            except Survey.DoesNotExist:
                from esp.middleware import ESPError
                raise ESPError('Selected survey does not exist for this program.', log=False)

            imported_count = 0
            rows_data = request.POST.getlist('row_data')
            
            try:
                for row_json in rows_data:
                    row = json.loads(row_json)
                try:
                    question_type = QuestionType.objects.get(id=row['question_type_id'])
                except QuestionType.DoesNotExist:
                    continue
                Question.objects.create(
                    survey=survey,
                    name=row['question_text'],
                    question_type=question_type,
                    _param_values=row.get('param_values', ''),
                    per_class=row['per_class'],
                    seq=row['seq'],
                )
                imported_count += 1

                except (ValueError, KeyError, json.JSONDecodeError):

                from esp.middleware import ESPError

                raise ESPError('There was a problem with the submitted import data. Please restart the CSV import process.', log=False)


                context['imported_count'] = imported_count
            context['survey'] = survey
            return render_to_response('program/modules/surveymanagement/csv_import_done.html', request, context)

        elif request.method == 'POST':
            # Step 1: Parse and validate CSV, show preview
            form = CSVQuestionImportForm(request.POST, request.FILES, cur_prog=prog)
            if form.is_valid():
                csv_file = form.cleaned_data['csv_file']
                survey = form.cleaned_data['survey']
                parsed_rows, errors = parse_csv(csv_file)

                # Prepare row data for the confirmation form
                rows_for_template = []
                for row in parsed_rows:
                    row_data = {
                        'question_text': row['question_text'],
                        'question_type_id': row['question_type'].id,
                        'per_class': row['per_class'],
                        'seq': row['seq'],
                        'param_values': row['param_values'],
                    }
                    rows_for_template.append({
                        'question_text': row['question_text'],
                        'question_type_name': row['question_type'].name,
                        'question_type_id': row['question_type'].id,
                        'per_class': row['per_class'],
                        'seq': row['seq'],
                        'param_values': row['param_values'],
                        'row_number': row['row_number'],
                        'json_data': json.dumps(row_data),
                    })

                context.update({
                    'parsed_rows': rows_for_template,
                    'errors': errors,
                    'survey': survey,
                    'csv_import_form': form,
                })
                return render_to_response('program/modules/surveymanagement/csv_import.html', request, context)
            else:
                # Form is invalid: preserve the bound form so errors are displayed
                return self.survey_manage(request, tl, one, two, module, 'manage', prog, extra_context={'csv_import_form': form})
        else:
            return self.survey_manage(request, tl, one, two, module, 'manage', prog)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'

