" A view to show surveys. "

__author__    = "$LastChangedBy$"
__date__      = "$LastChangedDate$"
__rev__       = "$LastChangedRevision$"
__headurl__   = "$HeadURL$"
__license__   = "GPL v2"
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

import datetime
from django.db import models
from esp.datatree.models import *
from esp.users.models import UserBit, ESPUser
from esp.program.models import Program, ClassCategories
from esp.survey.models import Question, Survey, SurveyResponse, Answer
from esp.web.util import render_to_response
from esp.web.util.latex import render_to_latex
from esp.program.modules.base import needs_admin
from esp.middleware import ESPError
from django.http import Http404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required

@login_required
def survey_view(request, tl, program, instance):

    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404

    user = ESPUser(request.user)
    
    if (tl == 'teach' and not user.isTeacher()) or (tl == 'learn' and not user.isStudent()):
        raise ESPError(False), 'You need to be a program participant (i.e. student or teacher, not parent or educator) to participate in this survey.  Please contact the directors directly if you have additional feedback.'

    if request.GET.has_key('done'):
        return render_to_response('survey/completed_survey.html', request, prog.anchor, {'prog': prog})
    
    if tl == 'learn':
        sv = GetNode('V/Flags/Survey/Filed')
    else:
        sv = GetNode('V/Flags/TeacherSurvey/Filed')

    if UserBit.UserHasPerms(request.user, prog.anchor, sv):
        raise ESPError(False), "You've already filled out the survey.  Thanks for responding!"

    surveys = prog.getSurveys().filter(category = tl).select_related()

    if request.REQUEST.has_key('survey_id'):
        try:
            s_id = int( request.REQUEST['survey_id'] )
            surveys = surveys.filter(id=s_id) # We want to filter, not get: ID could point to a survey that doesn't exist for this program, or at all
        except ValueError:
            pass

    if len(surveys) < 1:
        raise ESPError(False), "Sorry, no such survey exists for this program!"

    if len(surveys) > 1:
        return render_to_response('survey/choose_survey.html', request, prog.anchor, { 'surveys': surveys, 'error': request.POST }) # if request.POST, then we shouldn't have more than one survey any more...

    survey = surveys[0]

    if request.POST:
        response = SurveyResponse()
        response.survey = survey
        response.save()
        
        ub = UserBit(user=request.user, verb=sv, qsc=prog.anchor)
        ub.save()
        
        response.set_answers(request.POST, save=True)

        return HttpResponseRedirect(request.path + "?done")
    else:
        questions = survey.questions.filter(anchor = prog.anchor).order_by('seq')
        perclass_questions = survey.questions.filter(anchor__name="Classes", anchor__parent = prog.anchor)
        
        classes = sections = timeslots = []
        if tl == 'learn':
            classes = user.getEnrolledClasses(prog, request)
            timeslots = prog.getTimeSlots().order_by('start')
            for ts in timeslots:
                # The order by string really means "title"
                ts.classsections = prog.sections().filter(meeting_times=ts).exclude(meeting_times__start__lt=ts.start).order_by('parent_class__anchor__friendly_name').distinct()
                for sec in ts.classsections:
                    if user in sec.students():
                        sec.selected = True
        elif tl == 'teach':
            classes = user.getTaughtClasses(prog)
            sections = user.getTaughtSections(prog).order_by('parent_class__anchor__friendly_name')

        context = {
            'survey': survey,
            'questions': questions,
            'perclass_questions': perclass_questions,
            'program': prog,
            'classes': classes,
            'sections': sections,
            'timeslots': timeslots,
        }

        return render_to_response('survey/survey.html', request, prog.anchor, context)

def get_survey_info(request, tl, program, instance):
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404

    user = ESPUser(request.user)
    
    if (tl == 'teach' and user.isTeacher()):
        surveys = prog.getSurveys().filter(category = 'learn').select_related()
    elif (tl == 'manage' and user.isAdmin(prog.anchor)):
        #   Meerp, no problem... I took care of it.   -Michael
        surveys = prog.getSurveys().select_related()
        if request.REQUEST.has_key('teacher_id'):
            t_id = int( request.REQUEST['teacher_id'] )
            teachers = ESPUser.objects.filter(id=t_id)
            if len(teachers) > 0:
                user = teachers[0]
                if user.isTeacher():
                    surveys = prog.getSurveys().filter(category = 'learn').select_related()
                else:
                    user = ESPUser(request.user)
    else:
        raise ESPError(False), 'You need to be a teacher or administrator of this program to review survey responses.'
    
    if request.REQUEST.has_key('survey_id'):
        try:
            s_id = int( request.REQUEST['survey_id'] )
            surveys = surveys.filter(id=s_id) # We want to filter, not get: ID could point to a survey that doesn't exist for this program, or at all
        except ValueError:
            pass
    
    if len(surveys) < 1:
        raise ESPError(False), "Sorry, no such survey exists for this program!"

    return (user, prog, surveys)
    

def display_survey(user, prog, surveys, request, tl, format):
    """ Wrapper doing the necessary work for the survey output. """
    from esp.program.models import ClassSubject, ClassSection
    
    perclass_data = []
    
    def getByIdOrNone(model, key):
        q = model.objects.filter(id = request.REQUEST.get(key, None))[:1]
        if q:
            return q[0]
        return None
    
    sec = getByIdOrNone(ClassSection, 'classsection_id')
    cls = getByIdOrNone(ClassSubject, 'classsubject_id')
    
    if tl == 'manage' and not request.REQUEST.has_key('teacher_id'):
        #   In the manage category, pack the data in as extra attributes to the surveys
        surveys = list(surveys)
        for s in surveys:
            questions = s.questions.filter(anchor = prog.anchor).order_by('seq')
            s.display_data = {'questions': [ { 'question': y, 'answers': Answer.objects.filter(question=y) } for y in questions ]}
            questions2 = s.questions.filter(anchor__parent = prog.anchor, question_type__is_numeric = True).order_by('seq')
            s.display_data['questions'].extend([{ 'question': y, 'answers': Answer.objects.filter(question=y) } for y in questions2])
    else:
        perclass_questions = surveys[0].questions.filter(anchor__name="Classes", anchor__parent = prog.anchor).order_by('seq')
        surveys = []
        classes = []
        if sec is not None:
            classes = [ sec ]
        elif cls is not None:
            classes = cls.get_sections()
        elif tl == 'teach' or tl == 'manage':
            #   In the teach category, show only class-specific questions
            classes = user.getTaughtSections(prog).order_by('parent_class', 'id')
        perclass_data = [ { 'class': x, 'questions': [ { 'question': y, 'answers': y.answer_set.filter(anchor__in=(x.anchor, x.parent_class.anchor)) } for y in perclass_questions ] } for x in classes ]
    
    context = {'user': user, 'surveys': surveys, 'program': prog, 'perclass_data': perclass_data}
    
    #   Choose+use appropriate output format
    if format == 'html':
        return render_to_response('survey/review.html', request, prog.anchor, context)
    elif format == 'tex':
        return render_to_latex('survey/review.tex', context, 'pdf')

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
        raise ESPError(), "Can't find the program %s/%s" % (program, instance)

    user = ESPUser(request.user)
    
    survey_response = None
    ints = request.REQUEST.items()
    if len(ints) == 1:
        srs = SurveyResponse.objects.filter(id=ints[0][0])
        if len(srs) == 1:
            survey_response = srs[0]
    if survey_response is None:
        raise ESPError(False), 'Ideally this page should give you some way to pick an individual response. For now I guess you should go back to <a href="review">reviewing the whole survey</a>.'
    
    if tl == 'manage' and user.isAdmin(prog.anchor):
        answers = survey_response.answers.order_by('anchor', 'question')
        classes_only = False
    elif tl == 'teach':
        class_anchors = [x['anchor'] for x in user.getTaughtClasses().values('anchor')]
        answers = survey_response.answers.filter(anchor__in=class_anchors).order_by('anchor', 'question')
        classes_only = True
    else:
        raise ESPError(False), 'You need to be a teacher or administrator of this program to review survey responses.'
    
    context = {'user': user, 'program': prog, 'response': survey_response, 'answers': answers, 'classes_only': classes_only }
    
    return render_to_response('survey/review_single.html', request, prog.anchor, context)

# To be replaced with something more useful, eventually.
@login_required
def top_classes(request, tl, program, instance):
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404
    
    user = ESPUser(request.user)
    
    if (tl == 'manage' and user.isAdmin(prog.anchor)):
        surveys = prog.getSurveys().filter(category = 'learn').select_related()
    else:
        raise ESPError(False), 'You need to be a teacher or administrator of this program to review survey responses.'
    
    if request.REQUEST.has_key('survey_id'):
        try:
            s_id = int( request.REQUEST['survey_id'] )
            surveys = surveys.filter(id=s_id) # We want to filter, not get: ID could point to a survey that doesn't exist for this program, or at all
        except ValueError:
            pass
    
    if len(surveys) < 1:
        raise ESPError(False), 'Sorry, no such survey exists for this program!'

    if len(surveys) > 1:
        return render_to_response('survey/choose_survey.html', request, prog.anchor, { 'surveys': surveys, 'error': request.POST }) # if request.POST, then we shouldn't have more than one survey any more...
    
    survey = surveys[0]
    
    
    if tl == 'manage':
        classes = prog.classes()
        rating_questions = survey.questions.filter(name__contains='overall rating')
        if len(rating_questions) < 1:
            raise ESPError(False), 'Couldn\'t find an "overall rating" question in this survey.'
        rating_question = rating_questions[0]
        
        rating_cut = 0.0
        try:
            rating_cut = float( rating_question.get_params()['number_of_ratings'] ) - 1
        except ValueError:
            pass
        if request.REQUEST.has_key('rating_cut'):
            try:
                rating_cut = float( request.REQUEST['rating_cut'] )
            except ValueError:
                pass
            
        num_cut = 1
        if request.REQUEST.has_key('num_cut'):
            try:
                num_cut = int( request.REQUEST['num_cut'] )
            except ValueError:
                pass
        
        categories = prog.class_categories.all().order_by('category')
        
        perclass_data = []
        initclass_data = [ { 'class': x, 'ratings': [ x.answer for x in Answer.objects.filter(anchor=x.anchor, question=rating_question) ] } for x in classes ]
        for c in initclass_data:
            c['numratings'] = len(c['ratings'])
            if c['numratings'] < num_cut:
                continue
            c['avg'] = sum(c['ratings']) * 1.0 / c['numratings']
            if c['avg'] < rating_cut:
                continue
            teachers = list(c['class'].teachers())
            c['teacher'] = teachers[0]
            c['numteachers'] = len(teachers)
            if c['numteachers'] > 1:
                c['coteachers'] = teachers[1:]
            del c['ratings']
            perclass_data.append(c)
    context = { 'survey': survey, 'program': prog, 'perclass_data': perclass_data, 'rating_cut': rating_cut, 'num_cut': num_cut, 'categories': categories }
    
    return render_to_response('survey/top_classes.html', request, prog.anchor, context)
