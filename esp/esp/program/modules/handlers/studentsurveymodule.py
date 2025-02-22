
from __future__ import absolute_import
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
from esp.program.modules.base import ProgramModuleObj, needs_student_in_grade, meets_deadline, main_call
from esp.tagdict.models import Tag
from esp.users.models    import ESPUser
from django.db.models.query   import Q
from esp.survey.views   import survey_view

import datetime

class StudentSurveyModule(ProgramModuleObj):
    doc = """A module for students to take surveys about the program and/or classes."""

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Student Surveys",
            "link_title": "Student Surveys",
            "module_type": "learn",
            "seq": 9999,
            "choosable": 1,
        } ]

    def students(self, QObject = False):
        event="student_survey"
        program=self.program

        if QObject:
            return {'student_survey': Q(record__program=program) & Q(record__event__name=event)}
        return {'student_survey': ESPUser.objects.filter(record__program=program, record__event__name=event).distinct()}

    def studentDesc(self):
        return {'student_survey': """Students who filled out the survey"""}

    def isStep(self):
        return (Tag.getBooleanTag('student_survey_isstep', program=self.program) and
                self.program.getTimeSlots()[0].start < datetime.datetime.now() and
                self.program.getSurveys().filter(category = "learn").exists())

    @main_call
    @needs_student_in_grade
    @meets_deadline('/Survey')
    def survey(self, request, tl, one, two, module, extra, prog):
        return survey_view(request, tl, one, two)

    class Meta:
        proxy = True
        app_label = 'modules'
