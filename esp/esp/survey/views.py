" A view to show surveys. "

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

import datetime
import xlwt
import re
from cStringIO import StringIO
from django.db import models
from django.db.models import Q
from esp.users.models import ESPUser, Record, admin_required
from esp.program.models import Program, ClassCategories, StudentRegistration, RegistrationType, ClassSection
from esp.survey.models import Question, Survey, SurveyResponse, Answer
from esp.utils.web import render_to_response
from esp.utils.latex import render_to_latex
from esp.program.modules.base import needs_admin
from esp.middleware import ESPError
from esp.tagdict.models import Tag
from esp.users.forms.generic_search_form import ApprovedTeacherSearchForm
from django.http import Http404, HttpResponse
from wsgiref.util import FileWrapper
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Min

@login_required
def survey_view(request, tl, program, instance, template = 'survey/survey.html', context = {}):
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404

    user = request.user
    view_list = True

    context['tl'] = tl
    if tl in ['teach', 'learn']:
        filters = [x.strip() for x in Tag.getProgramTag('survey_' + {'learn': "student", 'teach': "teacher"}[tl] + '_filter', prog).split(",") if x.strip()]
        if len(filters) > 0:
            if tl == 'learn':
                users = prog.students()
            else:
                users = prog.teachers()
            if not user.isAdmin() and user not in {item for sublist in [users[filter] for filter in filters if filter in users] for item in sublist}:
                descs = prog.getListDescriptions()
                raise ESPError('Only ' + " or ".join([descs[filter].lower() for filter in filters if filter in descs]) + ' may participate in this survey.  Please contact the directors directly if you have additional feedback.', log=False)

    student_results = False
    if tl == 'learn':
        event = "student_survey"
    else:
        event = "teacher_survey"
        student_results = prog.getSurveys().filter(category = "learn", questions__per_class=True).exists()

    surveys = prog.getSurveys().filter(category = tl).select_related()

    context['survey_id'] = request.GET.get('survey_id', None)
    if 'survey_id' in request.GET:
        try:
            s_id = int( request.GET['survey_id'] )
            surveys = surveys.filter(id=s_id) # We want to filter, not get: ID could point to a survey that doesn't exist for this program, or at all
        except ValueError:
            pass

    if len(surveys) < 1:
        if student_results:
            survey = None
        else:
            raise ESPError("Sorry, no such survey exists for this program!", log=False)
    elif len(surveys) > 1:
        return render_to_response('survey/choose_survey.html', request, { 'surveys': surveys, 'student_results': student_results, 'error': request.POST }) # if request.POST, then we shouldn't have more than one survey any more...
    else:
        survey = surveys[0]

    # Section-specific survey
    section = None
    questions = perclass_questions = classes = []
    submitted = general = general_available = completed = section_surveys = general_survey = False
    if 'sec' in request.GET:
        sections = ClassSection.objects.filter(id=request.GET['sec'], parent_class__parent_program=prog)
        if len(sections) == 1:
            section = sections[0]
            if StudentRegistration.objects.filter(section=section, user=user, relationship__name="SurveyCompleted").exists():
                completed = True
            else:
                if request.POST:
                    response = SurveyResponse()
                    response.survey = survey
                    response.save()

                    # Set Student Registration to mark section survey as completed
                    survey_completed = RegistrationType.objects.get_or_create(name = 'SurveyCompleted', category = "student")[0]
                    sr = StudentRegistration(user = user, section = section, relationship = survey_completed)
                    sr.save()

                    response.set_answers(request.POST, save=True)
                    submitted = True
                else:
                    perclass_questions = survey.questions.filter(per_class = True)
                    view_list = False

    # General program survey
    elif 'general' in request.GET:
        general = True
        if Record.user_completed(user, event, prog):
            completed = True
        else:
            if request.POST:
                response = SurveyResponse()
                response.survey = survey
                response.save()

                # Set record to mark general survey as completed
                r = Record(user=user, event=event, program=prog, time=datetime.datetime.now())
                r.save()

                response.set_answers(request.POST, save=True)
                submitted = True
            else:
                questions = survey.questions.filter(per_class = False).order_by('seq')
                if tl == 'learn':
                    classes = user.getEnrolledClasses(prog)
                elif tl == 'teach':
                    classes = user.getTaughtClasses(prog)
                view_list = False

    sections = []
    if view_list and survey:
        completed_sections = ClassSection.objects.filter(parent_class__parent_program=prog, studentregistration__user=user, studentregistration__relationship__name="SurveyCompleted")
        if tl == 'learn':
            # Get a student's enrolled sections
            sections = ClassSection.objects.filter(id__in=[sec.id for sec in user.getEnrolledSections(prog)], status__gt=0).annotate(start=Min('meeting_times__start')).order_by('start')
        else:
            # Get a teacher's taught sections
            sections = user.getTaughtSections(prog).filter(status__gt=0).annotate(start=Min('meeting_times__start')).order_by('start')
            sections = [sec for sec in sections if sec.meeting_times.count() > 0]
        # Mark sections for whether they've started yet and whether the user has filled out a survey for them yet
        for sec in sections:
            sec.started = sec.start < datetime.datetime.now()
            sec.completed = sec in completed_sections

        context['general_done'] = Record.user_completed(user, event, prog)
        # Is this the best way to trigger the availability of the general program survey?
        general_available = any([sec.started for sec in sections])
        general_survey = survey.questions.filter(per_class = False).exists()
        section_surveys = survey.questions.filter(per_class = True).exists()

    context.update({
        'program': prog,
        'questions': questions,
        'perclass_questions': perclass_questions,
        'section': section,
        'sections': sections,
        'view_list': view_list,
        'submitted': submitted,
        'general': general,
        'general_available': general_available,
        'completed': completed,
        'classes': classes,
        'section_surveys': section_surveys,
        'general_survey': general_survey,
        'student_results': student_results
        })
    return render_to_response(template, request, context)

def get_survey_info(request, tl, program, instance):
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404

    user = request.user

    if (tl == 'teach' and user.isTeacher()):
        surveys = prog.getSurveys().filter(category = 'learn').select_related()
    elif (tl == 'manage' and user.isAdmin(prog)):
        #   Meerp, no problem... I took care of it.   -Michael
        surveys = prog.getSurveys().order_by('category').select_related()
        t_id = None
        if 'teacher_id' in request.GET:
            t_id = int( request.GET['teacher_id'] )
        elif 'teacher_id' in request.POST:
            t_id = int( request.POST['teacher_id'] )
        elif 'target_user' in request.POST:
            form = ApprovedTeacherSearchForm(request.POST)
            if form.is_valid():
                t_id = form.cleaned_data['target_user'].id
        if t_id:
            teachers = ESPUser.objects.filter(id=t_id)
            if len(teachers) > 0:
                user = teachers[0]
                if user.isTeacher():
                    surveys = prog.getSurveys().filter(category = 'learn').select_related()
                else:
                    user = request.user
    else:
        raise ESPError('You need to be a teacher or administrator of this program to review survey responses.', log=False)

    if 'survey_id' in request.GET:
        try:
            s_id = int( request.GET['survey_id'] )
            surveys = surveys.filter(id=s_id) # We want to filter, not get: ID could point to a survey that doesn't exist for this program, or at all
        except ValueError:
            pass

    if len(surveys) < 1:
        raise ESPError("Sorry, no such survey exists for this program!", log=False)

    return (user, prog, surveys)


def display_survey(user, prog, surveys, request, tl, format, template = 'survey/review.html', context = {}):
    """ Wrapper doing the necessary work for the survey output. """
    from esp.program.models import ClassSubject, ClassSection

    def getByIdOrNone(model, key):
        q = model.objects.filter(id = request.GET.get(key, None))[:1]
        if q:
            return q[0]
        q = model.objects.filter(id = request.POST.get(key, None))[:1]
        if q:
            return q[0]
        return None

    teacher_form = None
    sec = getByIdOrNone(ClassSection, 'classsection_id')
    cls = getByIdOrNone(ClassSubject, 'classsubject_id')
    if tl == 'manage' and 'target_user' in request.POST:
        teacher_form = ApprovedTeacherSearchForm(request.POST, prog = prog)
        if teacher_form.is_valid():
            teacher = teacher_form.cleaned_data['target_user']
        else:
            teacher = None
    else:
        teacher = getByIdOrNone(ESPUser, 'teacher_id')

    survey_list = []
    perclass_data = []
    subject_ct=ContentType.objects.get(app_label="program",model="classsubject")
    section_ct=ContentType.objects.get(app_label="program",model="classsection")
    if tl == 'manage' and teacher is None and sec is None and cls is None:
        #   In the manage category, pack the data in as extra attributes to the surveys
        survey_list = list(surveys)
        for s in survey_list:
            questions = s.questions.filter(per_class=False).order_by('-question_type__is_numeric', 'seq')
            s.display_data = {'questions': [ { 'question': y, 'answers': y.answer_set.all() } for y in questions ]}
            classes = prog.sections().order_by('parent_class', 'id')
            perclass_questions = s.questions.filter(per_class=True).order_by('-question_type__is_numeric', 'seq')
            s.perclass_data = [ { 'class': x, 'questions': [ { 'question': y, 'answers': y.answer_set.filter(Q(content_type=section_ct,object_id=x.id) | Q(content_type=subject_ct,object_id=x.parent_class.id)) } for y in perclass_questions ] } for x in classes ]
    else:
        perclass_questions = surveys[0].questions.filter(per_class=True).order_by('-question_type__is_numeric', 'seq')
        classes = []
        if sec is not None:
            classes = [ sec ]
        elif cls is not None:
            classes = cls.get_sections()
        elif teacher is not None:
            classes = teacher.getTaughtSections(prog).order_by('parent_class', 'id')
        elif tl == 'teach':
            #   In the teach category, show only class-specific questions
            classes = user.getTaughtSections(prog).order_by('parent_class', 'id')
        perclass_data = [ { 'class': x, 'questions': [ { 'question': y, 'answers': y.answer_set.filter(Q(content_type=section_ct,object_id=x.id) | Q(content_type=subject_ct,object_id=x.parent_class.id)) } for y in perclass_questions ] } for x in classes ]

    if tl == 'manage':
        if teacher:
            teacher_form = ApprovedTeacherSearchForm(initial={'target_user': teacher.id}, prog = prog)
        elif teacher_form is None:
            teacher_form = ApprovedTeacherSearchForm(prog = prog)
    context['teacher_form'] = teacher_form
    context.update({'user': user, 'teacher': teacher, 'surveys': survey_list, 'program': prog, 'perclass_data': perclass_data, 'tl': tl})

    #   Choose+use appropriate output format
    if format == 'html':
        return render_to_response(template, request, context)
    elif format == 'tex':
        return render_to_latex(template, context, 'pdf')

def delist(x):
    if isinstance(x,list):
        return ', '.join(x)
    else:
        return x

def _encode_ascii(cell_label):
    if isinstance(cell_label, basestring):
        return str(cell_label.encode('ascii', 'xmlcharrefreplace'))
    else:
        return cell_label

def _worksheet_write(worksheet, r, c, label="", style=None):
    if style is None:
        worksheet.write(r, c, _encode_ascii(label))
    else:
        worksheet.write(r, c, _encode_ascii(label), style)

def dump_survey_xlwt(user, prog, surveys, request, tl):
    from esp.program.models import ClassSubject, ClassSection
    if tl == 'manage' and not 'teacher_id' in request.GET and not 'classsection_id' in request.GET and not 'classsubject_id' in request.GET:
        # Styles yoinked from <http://www.djangosnippets.org/snippets/1151/>
        datetime_style = xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss')
        wb=xlwt.Workbook()
        survey_index = 0
        for s in surveys:
            # Certain characters are forbidden in sheet names
            # See <https://github.com/python-excel/xlwt/blob/8f0afdc9b322129600d81e754cabd2944e7064f2/xlwt/Utils.py#L154>
            s.name = re.sub(r"['\[\]:\\?/*\x00]", "", s.name.encode('ascii', 'ignore'))
            s.category = re.sub(r"['\[\]:\\?/*\x00]", "", s.category.encode('ascii', 'ignore'))
            # The length of sheet names is limited to 31 characters
            survey_index += 1
            if len(s.name)>31:
                ws=wb.add_sheet("%d %s... (%s)" % (survey_index, s.name[:17], s.category[:5]))
            else:
                ws=wb.add_sheet(s.name)
            ws.write(0,0,'Response ID')
            ws.write(0,1,'Timestamp')
            qs=list(s.questions.filter(per_class=False).order_by('seq','id'))
            srs=list(s.surveyresponse_set.all().order_by('id'))
            i=2
            q_dict={}
            for q in qs:
                q_dict[q.id]=i
                _worksheet_write(ws,0,i,q.name)
                i+=1
            i=1
            sr_dict={}
            for sr in srs:
                sr_dict[sr.id]=i
                _worksheet_write(ws,i,0,sr.id)
                _worksheet_write(ws,i,1,sr.time_filled,datetime_style)
                i+=1
            for a in Answer.objects.filter(question__in=qs).order_by('id'):
                _worksheet_write(ws,sr_dict[a.survey_response_id],q_dict[a.question_id],delist(a.answer))
            #PER-CLASS QUESTIONS
            # The length of sheet names is limited to 31 characters
            if len(s.name)>19:
                ws_perclass=wb.add_sheet("%d %s... (%s, per-class)" % (survey_index, s.name[:5], s.category[:5]))
            else:
                ws_perclass=wb.add_sheet(s.name + " (per-class)")
            ws_perclass.write(0,0,"Response ID")
            ws_perclass.write(0,1,"Timestamp")
            ws_perclass.write(0,2,"Class Code")
            ws_perclass.write(0,3,"Class Title")
            qs_perclass=list(s.questions.filter(per_class=True).order_by('seq','id'))
            i=4
            q_dict_perclass={}
            for q in qs_perclass:
                q_dict_perclass[q.id]=i
                _worksheet_write(ws_perclass,0,i,q.name)
                i+=1
            i=1
            src_dict_perclass={}
            for a in Answer.objects.filter(question__in=qs_perclass).order_by('id').select_related('survey_response'):
                sr=a.survey_response
                cs=a.target
                if isinstance(cs, ClassSection):
                    key=(sr,cs)
                else:
                    key=sr
                if key in src_dict_perclass:
                    row=src_dict_perclass[key]
                else:
                    row=i
                    src_dict_perclass[key]=i
                    _worksheet_write(ws_perclass,i,0,sr.id)
                    _worksheet_write(ws_perclass,i,1,sr.time_filled,datetime_style)
                    if cs:
                        _worksheet_write(ws_perclass,i,2,cs.emailcode())
                        _worksheet_write(ws_perclass,i,3,cs.title())
                    i+=1
                _worksheet_write(ws_perclass,row,q_dict_perclass[a.question_id],delist(a.answer))
        out=StringIO()
        wb.save(out)
        response=HttpResponse(out.getvalue(),content_type='application/vnd.ms-excel')
        response['Content-Disposition']='attachment; filename=dump-%s.xls' % (prog.name)
        return response
    else:
        raise ESPError("You need to be an administrator to dump survey results.", log=False)

@admin_required
def survey_dump(request, tl, program, instance):
    """ A dump of all survey results in the given program. """

    (user, prog, surveys) = get_survey_info(request, tl, program, instance)
    return dump_survey_xlwt(user, prog, surveys, request, tl)

@login_required
def survey_review(request, tl, program, instance, template = 'survey/review.html', context = {}):
    """ A view of all the survey results pertaining to a particular user in the given program. """

    (user, prog, surveys) = get_survey_info(request, tl, program, instance)
    return display_survey(user, prog, surveys, request, tl, 'html', template, context)

@login_required
def survey_graphical(request, tl, program, instance, template = 'survey/review.tex', context = {}):
    """ A PDF view of the survey results with histograms. """

    (user, prog, surveys) = get_survey_info(request, tl, program, instance)
    return display_survey(user, prog, surveys, request, tl, 'tex', template, context)

@login_required
def survey_review_single(request, tl, program, instance, template = 'survey/review_single.html', context = {}):
    """ View a single survey response. """
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        #raise Http404
        raise ESPError("Can't find the program %s/%s" % (program, instance))

    user = request.user

    survey_response = None
    ints = request.GET.items()
    if len(ints) == 1:
        srs = SurveyResponse.objects.filter(id=ints[0][0])
        if len(srs) == 1:
            survey_response = srs[0]
    if survey_response is None:
        raise ESPError('Ideally this page should give you some way to pick an individual response. For now I guess you should go back to <a href="review">reviewing the whole survey</a>.', log=False)

    if tl == 'manage' and user.isAdmin(prog):
        answers = survey_response.answers.order_by('content_type','object_id', 'question')
        classes_only = False
        other_responses = None
    elif tl == 'teach':
        subject_ct=ContentType.objects.get(app_label="program",model="classsubject")
        section_ct=ContentType.objects.get(app_label="program",model="classsection")
        class_ids = [x["id"] for x in user.getTaughtClasses().values('id')]
        section_ids = [x["id"] for x in user.getTaughtSections().values('id')]
        answers = survey_response.answers.filter(content_type__in=[subject_ct, section_ct], object_id__in=(class_ids+section_ids)).order_by('content_type','object_id', 'question')
        classes_only = True
        other_responses = SurveyResponse.objects.filter(answers__content_type=subject_ct, answers__object_id__in=class_ids).order_by('id').distinct()
    else:
        raise ESPError('You need to be a teacher or administrator of this program to review survey responses.', log=False)

    context.update({'user': user, 'program': prog, 'response': survey_response, 'answers': answers, 'classes_only': classes_only, 'other_responses': other_responses })

    return render_to_response(template, request, context)

# To be replaced with something more useful, eventually.
@login_required
def top_classes(request, tl, program, instance):
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404

    user = request.user

    if (tl == 'manage' and user.isAdmin(prog)):
        surveys = prog.getSurveys().filter(category = 'learn').select_related()
    else:
        raise ESPError('You need to be a teacher or administrator of this program to review survey responses.', log=False)

    if 'survey_id' in request.GET:
        try:
            s_id = int( request.GET['survey_id'] )
            surveys = surveys.filter(id=s_id) # We want to filter, not get: ID could point to a survey that doesn't exist for this program, or at all
        except ValueError:
            pass

    if len(surveys) < 1:
        raise ESPError('Sorry, no such survey exists for this program!', log=False)

    if len(surveys) > 1:
        return render_to_response('survey/choose_survey.html', request, { 'surveys': surveys, 'error': request.POST }) # if request.POST, then we shouldn't have more than one survey any more...

    survey = surveys[0]


    if tl == 'manage':
        classes = prog.classes()
        rating_questions = survey.questions.filter(name__contains='overall rating')
        if len(rating_questions) < 1:
            raise ESPError('Couldn\'t find an "overall rating" question in this survey.', log=False)
        rating_question = rating_questions[0]

        rating_cut = 0.0
        try:
            rating_cut = float( rating_question.get_params()['number_of_ratings'] ) - 1
        except ValueError:
            pass
        if 'rating_cut' in request.GET:
            try:
                rating_cut = float( request.GET['rating_cut'] )
            except ValueError:
                pass

        num_cut = 1
        if 'num_cut' in request.GET:
            try:
                num_cut = int( request.GET['num_cut'] )
            except ValueError:
                pass

        categories = prog.class_categories.all().order_by('category')

        section_ct=ContentType.objects.get(app_label="program",model="classsection")

        perclass_data = []
        initclass_data = [ { 'class': cls, 'ratings': [ float(x.answer) for sec in cls.get_sections() for x in Answer.objects.filter(object_id=sec.id, content_type=section_ct, question=rating_question)] } for cls in classes ]
        for c in initclass_data:
            c['numratings'] = len(c['ratings'])
            if c['numratings'] < num_cut:
                continue
            c['avg'] = sum(c['ratings']) * 1.0 / c['numratings']
            if c['avg'] < rating_cut:
                continue
            teachers = list(c['class'].get_teachers())
            c['teacher'] = teachers[0] if len(teachers) > 0 else None
            c['numteachers'] = max(len(teachers), 1) #in case there are no teachers
            if c['numteachers'] > 1:
                c['coteachers'] = teachers[1:]
            del c['ratings']
            perclass_data.append(c)
    context = { 'survey': survey, 'program': prog, 'perclass_data': perclass_data, 'rating_cut': rating_cut, 'num_cut': num_cut, 'categories': categories }

    return render_to_response('survey/top_classes.html', request, context)
