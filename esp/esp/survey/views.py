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
from cStringIO import StringIO
from django.db import models
from django.db.models import Q
from esp.users.models import ESPUser, Record, admin_required
from esp.program.models import Program, ClassCategories
from esp.survey.models import Question, Survey, SurveyResponse, Answer
from esp.utils.web import render_to_response
from esp.utils.latex import render_to_latex
from esp.program.modules.base import needs_admin
from esp.middleware import ESPError
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.servers.basehttp import FileWrapper
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

@login_required
def survey_view(request, tl, program, instance):

    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404

    user = ESPUser(request.user)
    
    if (tl == 'teach' and not user.isTeacher()) or (tl == 'learn' and not user.isStudent()):
        raise ESPError('You need to be a program participant (i.e. student or teacher, not parent or educator) to participate in this survey.  Please contact the directors directly if you have additional feedback.', log=False)

    if request.GET.has_key('done'):
        return render_to_response('survey/completed_survey.html', request, {'prog': prog})
    
    if tl == 'learn':
        event = "student_survey"
    else:
        event = "teacher_survey"

    if Record.user_completed(user, event ,prog):
        raise ESPError("You've already filled out the survey.  Thanks for responding!", log=False)


    surveys = prog.getSurveys().filter(category = tl).select_related()

    if request.GET.has_key('survey_id'):
        try:
            s_id = int( request.GET['survey_id'] )
            surveys = surveys.filter(id=s_id) # We want to filter, not get: ID could point to a survey that doesn't exist for this program, or at all
        except ValueError:
            pass

    if len(surveys) < 1:
        raise ESPError("Sorry, no such survey exists for this program!", log=False)

    if len(surveys) > 1:
        return render_to_response('survey/choose_survey.html', request, { 'surveys': surveys, 'error': request.POST }) # if request.POST, then we shouldn't have more than one survey any more...

    survey = surveys[0]

    if request.POST:
        response = SurveyResponse()
        response.survey = survey
        response.save()
        
        r = Record(user=user, event=event, program=prog, time=datetime.datetime.now())
        r.save()
        
        response.set_answers(request.POST, save=True)

        return HttpResponseRedirect(request.path + "?done")
    else:
        questions = survey.questions.filter(per_class = False).order_by('seq')
        perclass_questions = survey.questions.filter(per_class = True)
        
        classes = sections = timeslots = []
        if tl == 'learn':
            classes = user.getEnrolledClasses(prog)
            enrolled_secs = user.getEnrolledSections(prog)
            timeslots = prog.getTimeSlots().order_by('start')
            for ts in timeslots:
                # The order by string really means "title"
                ts.classsections = prog.sections().filter(meeting_times=ts).exclude(meeting_times__start__lt=ts.start).order_by('parent_class__title').distinct()
                for sec in ts.classsections:
                    if sec in enrolled_secs:
                        sec.selected = True
        elif tl == 'teach':
            classes = user.getTaughtClasses(prog)
            sections = user.getTaughtSections(prog).order_by('parent_class__title')

        context = {
            'survey': survey,
            'questions': questions,
            'perclass_questions': perclass_questions,
            'program': prog,
            'classes': classes,
            'sections': sections,
            'timeslots': timeslots,
        }

        return render_to_response('survey/survey.html', request, context)

def get_survey_info(request, tl, program, instance):
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404

    user = ESPUser(request.user)
    
    if (tl == 'teach' and user.isTeacher()):
        surveys = prog.getSurveys().filter(category = 'learn').select_related()
    elif (tl == 'manage' and user.isAdmin(prog)):
        #   Meerp, no problem... I took care of it.   -Michael
        surveys = prog.getSurveys().select_related()
        if request.GET.has_key('teacher_id'):
            t_id = int( request.GET['teacher_id'] )
            teachers = ESPUser.objects.filter(id=t_id)
            if len(teachers) > 0:
                user = teachers[0]
                if user.isTeacher():
                    surveys = prog.getSurveys().filter(category = 'learn').select_related()
                else:
                    user = ESPUser(request.user)
    else:
        raise ESPError('You need to be a teacher or administrator of this program to review survey responses.', log=False)
    
    if request.GET.has_key('survey_id'):
        try:
            s_id = int( request.GET['survey_id'] )
            surveys = surveys.filter(id=s_id) # We want to filter, not get: ID could point to a survey that doesn't exist for this program, or at all
        except ValueError:
            pass
    
    if len(surveys) < 1:
        raise ESPError("Sorry, no such survey exists for this program!", log=False)

    return (user, prog, surveys)
    

def display_survey(user, prog, surveys, request, tl, format):
    """ Wrapper doing the necessary work for the survey output. """
    from esp.program.models import ClassSubject, ClassSection
    
    perclass_data = []
    
    def getByIdOrNone(model, key):
        q = model.objects.filter(id = request.GET.get(key, None))[:1]
        if q:
            return q[0]
        return None
    
    sec = getByIdOrNone(ClassSection, 'classsection_id')
    cls = getByIdOrNone(ClassSubject, 'classsubject_id')
    
    if tl == 'manage' and not request.GET.has_key('teacher_id') and sec is None and cls is None:
        #   In the manage category, pack the data in as extra attributes to the surveys
        surveys = list(surveys)
        for s in surveys:
            questions = s.questions.filter(per_class=False).order_by('seq')
            s.display_data = {'questions': [ { 'question': y, 'answers': y.answer_set.all() } for y in questions ]}
            questions2 = s.questions.filter(per_class=True, question_type__is_numeric = True).order_by('seq')
            s.display_data['questions'].extend([{ 'question': y, 'answers': Answer.objects.filter(question=y) } for y in questions2])
    else:
        perclass_questions = surveys[0].questions.filter(per_class=True).order_by('seq')
        surveys = []
        classes = []
        if sec is not None:
            classes = [ sec ]
        elif cls is not None:
            classes = cls.get_sections()
        elif tl == 'teach' or tl == 'manage':
            #   In the teach category, show only class-specific questions
            classes = user.getTaughtSections(prog).order_by('parent_class', 'id')
        subject_ct=ContentType.objects.get(app_label="program",model="classsubject")
        section_ct=ContentType.objects.get(app_label="program",model="classsection")
        perclass_data = [ { 'class': x, 'questions': [ { 'question': y, 'answers': y.answer_set.filter(Q(content_type=section_ct,object_id=x.id) | Q(content_type=subject_ct,object_id=x.parent_class.id)) } for y in perclass_questions ] } for x in classes ]
    
    context = {'user': user, 'surveys': surveys, 'program': prog, 'perclass_data': perclass_data}
    
    #   Choose+use appropriate output format
    if format == 'html':
        return render_to_response('survey/review.html', request, context)
    elif format == 'tex':
        return render_to_latex('survey/review.tex', context, 'pdf')

def delist(x):
    if isinstance(x,list):
        return ', '.join(x)
    else:
        return x

def dump_survey_xlwt(user, prog, surveys, request, tl):
    from esp.program.models import ClassSubject, ClassSection
    if tl == 'manage' and not request.GET.has_key('teacher_id') and not request.GET.has_key('classsection_id') and not request.GET.has_key('classsubject_id'):
        # Styles yoinked from <http://www.djangosnippets.org/snippets/1151/>
        datetime_style = xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss')
        wb=xlwt.Workbook()
        for s in surveys:
            if len(s.name)>31:
                ws=wb.add_sheet(s.name[:28] + "...")
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
                ws.write(0,i,q.name)
                i+=1
            i=1
            sr_dict={}
            for sr in srs:
                sr_dict[sr.id]=i
                ws.write(i,0,sr.id)
                ws.write(i,1,sr.time_filled,datetime_style)
                i+=1
            for a in Answer.objects.filter(question__in=qs).order_by('id'):
                ws.write(sr_dict[a.survey_response_id],q_dict[a.question_id],delist(a.answer))
            #PER-CLASS QUESTIONS
            if len(s.name)>19:
                ws_perclass=wb.add_sheet(s.name[:16] + "... (per-class)")
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
                ws_perclass.write(0,i,q.name)
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
                    ws_perclass.write(i,0,sr.id)
                    ws_perclass.write(i,1,sr.time_filled,datetime_style)
                    if cs:
                        ws_perclass.write(i,2,cs.emailcode())
                        ws_perclass.write(i,3,cs.title())
                    i+=1
                ws_perclass.write(row,q_dict_perclass[a.question_id],delist(a.answer))
        out=StringIO()
        wb.save(out)
        response=HttpResponse(out.getvalue(),content_type='application/vnd.ms-excel')
        response['Content-Disposition']='attachment; filename=dump.xls'
        return response
    else:
        raise ESPError("You need to be an administrator to dump survey results.", log=False)

@admin_required
def survey_dump(request, tl, program, instance):
    """ A dump of all survey results in the given program. """

    (user, prog, surveys) = get_survey_info(request, tl, program, instance)
    return dump_survey_xlwt(user, prog, surveys, request, tl)

@login_required
def survey_review(request, tl, program, instance):
    """ A view of all the survey results pertaining to a particular user in the given program. """

    (user, prog, surveys) = get_survey_info(request, tl, program, instance)
    return display_survey(user, prog, surveys, request, tl, 'html')

@login_required
def survey_graphical(request, tl, program, instance):
    """ A PDF view of the survey results with histograms. """
    
    (user, prog, surveys) = get_survey_info(request, tl, program, instance)
    return display_survey(user, prog, surveys, request, tl,'tex')

@login_required
def survey_review_single(request, tl, program, instance):
    """ View a single survey response. """
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        #raise Http404
        raise ESPError("Can't find the program %s/%s" % (program, instance))

    user = ESPUser(request.user)
    
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
    
    context = {'user': user, 'program': prog, 'response': survey_response, 'answers': answers, 'classes_only': classes_only, 'other_responses': other_responses }
    
    return render_to_response('survey/review_single.html', request, context)

# To be replaced with something more useful, eventually.
@login_required
def top_classes(request, tl, program, instance):
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404
    
    user = ESPUser(request.user)
    
    if (tl == 'manage' and user.isAdmin(prog)):
        surveys = prog.getSurveys().filter(category = 'learn').select_related()
    else:
        raise ESPError('You need to be a teacher or administrator of this program to review survey responses.', log=False)
    
    if request.GET.has_key('survey_id'):
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
        if request.GET.has_key('rating_cut'):
            try:
                rating_cut = float( request.GET['rating_cut'] )
            except ValueError:
                pass
            
        num_cut = 1
        if request.GET.has_key('num_cut'):
            try:
                num_cut = int( request.GET['num_cut'] )
            except ValueError:
                pass
        
        categories = prog.class_categories.all().order_by('category')
        
        subject_ct=ContentType.objects.get(app_label="program",model="classsubject")

        perclass_data = []
        initclass_data = [ { 'class': x, 'ratings': [ x.answer for x in Answer.objects.filter(object_id=x.id, content_type=subject_ct, question=rating_question) ] } for x in classes ]
        for c in initclass_data:
            c['numratings'] = len(c['ratings'])
            if c['numratings'] < num_cut:
                continue
            c['avg'] = sum(c['ratings']) * 1.0 / c['numratings']
            if c['avg'] < rating_cut:
                continue
            teachers = list(c['class'].get_teachers())
            c['teacher'] = teachers[0]
            c['numteachers'] = len(teachers)
            if c['numteachers'] > 1:
                c['coteachers'] = teachers[1:]
            del c['ratings']
            perclass_data.append(c)
    context = { 'survey': survey, 'program': prog, 'perclass_data': perclass_data, 'rating_cut': rating_cut, 'num_cut': num_cut, 'categories': categories }
    
    return render_to_response('survey/top_classes.html', request, context)
