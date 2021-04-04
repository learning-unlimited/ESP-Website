
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
#from esp.program.modules.forms.teacherreg import TeacherEventSignupForm
#from esp.program.modules import module_ext
from esp.utils.web import render_to_response
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
#from django.core.mail import send_mail
from django.db.models.query import Q
#from esp.miniblog.models import Entry
#from esp.cal.models import Event
from esp.users.models import ESPUser, User, Record
from esp.customforms.models import Form
from esp.customforms.DynamicForm import FormHandler
from esp.tagdict.models import Tag
from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request
from datetime import datetime
import re

class TeacherQuizController(object):

    twoday_pattern = re.compile('^[^0-9]*([0-9]+)[^0-9]+([0-9]+)[^0-9]*$')

    def __init__(self, program, *args, **kwargs):
        super(TeacherQuizController, self).__init__(*args, **kwargs)
        self.program = program

        # Some setup
        self.event = "teacher_quiz_done"

    def markCompleted(self, user):
        """Mark a user as having completed the quiz."""
        r,created = Record.objects.get_or_create(user=user, event=self.event, program=self.program)
        if not created:
            r.time=datetime.now()
            r.save()

    def unmarkCompleted(self, user):
        """Mark a user as not having completed the quiz."""
        Record.objects.filter(user=user, event=self.event, program=self.program).delete()

    def isCompleted(self, user):
        """Has a user completed the quiz?"""
        if Record.objects.filter(user=user, event=self.event, program=self.program).count()>0:
            return True
        return False

class TeacherQuizModule(ProgramModuleObj):
    # Initialization
    def __init__(self, *args, **kwargs):
        super(TeacherQuizModule, self).__init__(*args, **kwargs)
        self.event="teacher_quiz_done"

    @property
    def controller(self):
        if hasattr(self, '_controller'):
            return self._controller
        return TeacherQuizController(self.program)

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

        qo = Q(record__event=self.event,
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
        return self.controller.isCompleted(get_current_request().user)

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

        form_wizard = FormHandler(cf, request, request.user).get_wizard()
        form_wizard.curr_request = request

        if request.method == 'POST':
            form = form_wizard.get_form(0, request.POST, request.FILES)
            if form.is_valid():
                form_wizard.done([form])
                self.controller.markCompleted(request.user)
                return self.goToCore(tl)
        else:
            form = form_wizard.get_form(0)

        return render_to_response(self.baseDir()+'quiz.html', request, {'prog':prog, 'form': form})

    def isStep(self):
        custom_form_id = Tag.getProgramTag('quiz_form_id', self.program)
        return custom_form_id and Form.objects.filter(id=int(custom_form_id)).exists()

    class Meta:
        proxy = True
        app_label = 'modules'
