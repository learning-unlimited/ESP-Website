
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, meets_deadline, main_call
from esp.tagdict.models import Tag
from esp.users.models    import ESPUser
from django.db.models.query   import Q
from esp.survey.views   import survey_view, survey_review, survey_graphical, survey_review_single

import datetime

class TeacherSurveyModule(ProgramModuleObj):
    """ A module for people to take surveys. """

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Teacher Surveys",
            "link_title": "Teacher Surveys",
            "module_type": "teach",
            "seq": 9999,
            "choosable": 1,
        } ]

    def teachers(self, QObject = False):
        event="teacher_survey"
        program=self.program

        if QObject:
            return {'teacher_survey': Q(record__program=program) & Q(record__event=event)}
        return {'teacher_survey': ESPUser.objects.filter(record__program=program, record__event=event).distinct()}

    def teacherDesc(self):
        return {'teacher_survey': """Teachers who filled out the survey"""}

    def isStep(self):
        return (Tag.getBooleanTag('teacher_survey_isstep', program=self.program) and
                self.program.getTimeSlots()[0].start < datetime.datetime.now() and
                self.program.getSurveys().filter(category__in = ["learn","teach"]).exists())

    @main_call
    @needs_teacher
    @meets_deadline('/Survey')
    def survey(self, request, tl, one, two, module, extra, prog):
        if extra is None or extra == '':
            return survey_view(request, tl, one, two)
        elif extra == 'review':
            return survey_review(request, tl, one, two)
        elif extra == 'review_pdf':
            return survey_graphical(request, tl, one, two)
        elif extra == 'review_single':
            return survey_review_single(request, tl, one, two)

    surveys = survey

    class Meta:
        proxy = True
        app_label = 'modules'
