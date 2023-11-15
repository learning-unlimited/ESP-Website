
from __future__ import absolute_import
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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
from esp.program.modules.handlers.teachercustomformmodule import TeacherCustomFormModule

from esp.users.models import ESPUser, Record, RecordType
from esp.customforms.models import Form
from esp.customforms.DynamicForm import FormHandler, ComboForm
from esp.tagdict.models import Tag

from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request

from django.db.models.query import Q

class TeacherQuizComboForm(ComboForm):
    template_name = "program/modules/customformmodule/custom_form.html"
    event = "teacher_quiz_done"
    program = None

    def done(self, form_list, **kwargs):
        # Delete old records, if any exist, and then make a new one
        rt = RecordType.objects.get(name=self.event)
        Record.objects.filter(user=self.curr_request.user, program=self.program, event=rt).delete()
        Record.objects.create(user=self.curr_request.user, program=self.program, event=rt)
        return super(TeacherQuizComboForm, self).done(form_list=form_list, redirect_url = '/teach/'+self.program.getUrlBase()+'/teacherreg', **kwargs)

class TeacherQuizModule(ProgramModuleObj):
    doc = """Serves a custom form quiz during teacher registration."""

    # Initialization
    def __init__(self, *args, **kwargs):
        super(TeacherQuizModule, self).__init__(*args, **kwargs)
        self.event="teacher_quiz_done"

    # General Info functions
    @classmethod
    def module_properties(cls):
        return [ {
            "module_type": "teach",
            'required': False,
            'admin_title': 'Teacher Logistics Quiz',
            'link_title': 'Take the Teacher Logistics Quiz',
            'seq': 5,
            'choosable': 0,
        }, ]

    def teachers(self, QObject = False):
        """Returns lists of teachers who've completed the teacher quiz."""

        qo = Q(record__event__name=self.event,
               record__program=self.program)
        if QObject is True:
            return {
                'quiz_done': qo,
            }
        else:
            return {
                'quiz_done': ESPUser.objects.filter(qo).distinct(),
            }

    def teacherDesc(self):
        return {
            'quiz_done': """Teachers who have completed the teacher logistics quiz""",
        }

    # Per-user info
    def isCompleted(self):
        """Return true if user has filled out the teacher quiz."""
        if hasattr(self, 'user'):
            user = self.user
        else:
            user = get_current_request().user
        return Record.objects.filter(user=user, program=self.program, event__name=self.event).exists()

    # Views
    @main_call
    @needs_teacher
    @meets_deadline('/Quiz')
    def quiz(self, request, tl, one, two, module, extra, prog):
        custom_form_id = Tag.getProgramTag('quiz_form_id', prog)
        if custom_form_id:
            cf = Form.objects.get(id=int(custom_form_id))
        else:
            raise ESPError('Cannot find an appropriate form for the quiz.  Please ask your administrator to create a form and set the quiz_form_id Tag.')

        #   If the user already filled out the form, use their earlier response for the initial values
        if self.isCompleted():
            prev_result_data = TeacherCustomFormModule.get_prev_data(cf, request)
            return FormHandler(cf, request, request.user).get_wizard_view(wizard_view=TeacherQuizComboForm, initial_data = prev_result_data,
                               extra_context = {'prog': prog, 'qsd_name': 'teach:quizheader', 'module': self.module.link_title}, program = prog)
        else:
            return FormHandler(cf, request, request.user).get_wizard_view(wizard_view=TeacherQuizComboForm,
                               extra_context = {'prog': prog, 'qsd_name': 'teach:quizheader', 'module': self.module.link_title}, program = prog)

    def isStep(self):
        custom_form_id = Tag.getProgramTag('quiz_form_id', self.program)
        return custom_form_id and Form.objects.filter(id=int(custom_form_id)).exists()

    class Meta:
        proxy = True
        app_label = 'modules'
