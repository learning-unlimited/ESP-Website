
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_grade, CoreModule
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.users.models    import UserBit, ESPUser, User
from esp.datatree.models import GetNode
from esp.db.models      import Q
from esp.middleware     import ESPError
from esp.survey.models  import QuestionType, Question, Answer, SurveyResponse, Survey
from esp.survey.views   import survey_view, survey_review, survey_graphical, survey_review_single

import operator

class SurveyModule(ProgramModuleObj, CoreModule):

    def students(self, QObject = False):
        verb = GetNode('V/Flags/Survey/Filed')
        qsc  = GetNode("/".join(self.program_anchor_cached().tree_encode()))

        if QObject:
            return {'student_survey': self.getQForUser(Q(userbit__qsc = qsc) & Q(userbit__verb = verb))}
        return {'student_survey': User.objects.filter(userbit__qsc = qsc, userbit__verb = verb).distinct()}

    def teachers(self, QObject = False):
        verb = GetNode('V/Flags/TeacherSurvey/Filed')
        qsc  = GetNode("/".join(self.program_anchor_cached().tree_encode()))

        if QObject:
            return {'teacher_survey': self.getQForUser(Q(userbit__qsc = qsc) & Q(userbit__verb = verb))}
        return {'teacher_survey': User.objects.filter(userbit__qsc = qsc, userbit__verb = verb).distinct()}

    def studentDesc(self):
        return {'student_survey': """Students who filled out the survey"""}

    def teacherDesc(self):
        return {'teacher_survey': """Teachers who filled out the survey"""}

    def isStep(self):
        return False

    def getNavBars(self):
        nav_bars = []
        if self.module.module_type == 'learn':
            if self.deadline_met('/Survey'):
                nav_bars.append({ 'link': '/learn/%s/survey/' % ( self.program.getUrlBase() ),
                        'text': '%s Survey' % ( self.program.niceSubName() ),
                        'section': 'learn'})
        elif self.module.module_type == 'teach':
            if self.deadline_met('/Survey'):                    
                nav_bars.append({ 'link': '/teach/%s/survey/' % ( self.program.getUrlBase() ),
                        'text': '%s Survey' % ( self.program.niceSubName() ),
                        'section': 'teach'})
                nav_bars.append({ 'link': '/teach/%s/survey/review' % ( self.program.getUrlBase() ),
                        'text': '%s Student Surveys' % ( self.program.niceSubName() ),
                        'section': 'teach'})

        return nav_bars
    
    def survey(self, request, tl, one, two, module, extra, prog):
        if extra is None or extra == '':
            return survey_view(request, tl, one, two)
        elif extra == 'review':
            return survey_review(request, tl, one, two)
        elif extra == 'review_pdf':
            return survey_graphical(request, tl, one, two)
        elif extra == 'review_single':
            return survey_review_single(request, tl, one, two)
        
