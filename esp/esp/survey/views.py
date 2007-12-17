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
from esp.datatree.models import DataTree, GetNode
from esp.users.models import UserBit, ESPUser
from esp.program.models import Program
from esp.survey.models import Question, Survey, SurveyResponse, Answer
from esp.web.util import render_to_response
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
        
        user.clear_enrollment_cache(prog)
        if tl == 'learn':
            classes = user.getEnrolledClasses(prog, request)
        elif tl == 'teach':
            classes = user.getTaughtClasses(prog)
        else:
            classes = []

        context = { 'survey': survey, 'questions': questions, 'perclass_questions': perclass_questions, 'program': prog, 'classes': classes }

        return render_to_response('survey/survey.html', request, prog.anchor, context)

@login_required
def survey_review(request, tl, program, instance):
    try:
        prog = Program.by_prog_inst(program, instance)
    except Program.DoesNotExist:
        raise Http404

    user = ESPUser(request.user)
    
    if (tl == 'teach' and user.isTeacher()):
        surveys = prog.getSurveys().filter(category = 'learn').select_related()
    elif (tl == 'manage' and user.isAdmin(prog.anchor)):
        raise ESPError(False), 'Meerp, sorry... I haven&apos;t written this part yet. -ageng'
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

    if len(surveys) > 1:
        return render_to_response('survey/choose_survey.html', request, prog.anchor, { 'surveys': surveys, 'error': request.POST }) # if request.POST, then we shouldn't have more than one survey any more...
    
    survey = surveys[0]
    
    if tl == 'teach':
        classes = user.getTaughtClasses(prog)
        perclass_questions = survey.questions.filter(anchor__name="Classes", anchor__parent = prog.anchor)
        perclass_data = [ { 'class': x, 'questions': [ { 'question': y, 'answers': [ x.answer for x in Answer.objects.filter(anchor=x.anchor, question=y) ] } for y in perclass_questions ] } for x in classes ]
    
    context = { 'survey': survey, 'program': prog, 'perclass_data': perclass_data }
    
    return render_to_response('survey/review.html', request, prog.anchor, context)
