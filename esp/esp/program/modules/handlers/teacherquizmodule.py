
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
  Email: web-team@lists.learningu.org
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
#from esp.program.modules.forms.teacherreg import TeacherEventSignupForm
#from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
#from django.core.mail import send_mail
from django.db.models.query import Q
#from esp.miniblog.models import Entry
from esp.datatree.models import GetNode, DataTree
#from esp.cal.models import Event
from esp.users.models import ESPUser, UserBit, User
from esp.customforms.models import Form
from esp.customforms.DynamicForm import FormHandler
from esp.tagdict.models import Tag
#from datetime import datetime
import re

class TeacherQuizController(object):

    twoday_pattern = re.compile('^[^0-9]*([0-9]+)[^0-9]+([0-9]+)[^0-9]*$')

    def __init__(self, program_or_anchor, *args, **kwargs):
        super(TeacherQuizController, self).__init__(*args, **kwargs)
        self.program_anchor = program_or_anchor
        # We'll also accept a program
        if hasattr(self.program_anchor, 'anchor'):
            self.program_anchor = self.program_anchor.anchor
        # Make a sad attempt at type safety
        if not isinstance(self.program_anchor, DataTree):
            raise TypeError("Argument to constructor should be Program or DataTree node.")
        # Some setup
        self.reg_verb = GetNode('V/Flags/Registration/Teacher/QuizDone')

    def _bitsByUser(self, user):
        """Get relevant UserBits (the "completed quiz" ones) for a user."""
        return UserBit.objects.filter(Q(user=user, qsc=self.program_anchor, verb=self.reg_verb) & UserBit.not_expired())

    def markCompleted(self, user):
        """Mark a user as having completed the quiz."""
        ub, created = UserBit.objects.get_or_create(user=user, qsc=self.program_anchor, verb=self.reg_verb)
        if not created:
            ub.renew()

    def unmarkCompleted(self, user):
        """Mark a user as not having completed the quiz."""
        ubs = self._bitsByUser(user)
        for ub in ubs:
            ub.expire()

    def isCompleted(self, user):
        """Has a user completed the quiz?"""
        if self._bitsByUser(user):
            return True
        return False

class TeacherQuizModule(ProgramModuleObj):
    # Initialization
    def __init__(self, *args, **kwargs):
        super(TeacherQuizModule, self).__init__(*args, **kwargs)
        self.reg_verb = GetNode('V/Flags/Registration/Teacher/QuizDone')

    @property
    def controller(self):
        if hasattr(self, '_controller'):
            return self._controller
        return TeacherQuizController(self.program_anchor_cached())

    # General Info functions
    @classmethod
    def module_properties(cls):
        return [ {
            "module_type": "teach",
            'required': False,
            'main_call': 'quiz',
            'admin_title': 'Teacher Logistics Quiz',
            'link_title': 'Take the Teacher Logistics Quiz',
            'seq': 5,
        }, ]

    def teachers(self, QObject = False):
        """Returns lists of teachers who've completed the teacher quiz."""

        qo = Q(
            userbit__verb = self.controller.reg_verb,
            userbit__qsc = self.program_anchor_cached(),
            ) & UserBit.not_expired(prefix='userbit__')
        if QObject is True:
            return {
                'quiz_done': self.getQForUser(qo),
            }
        else:
            return {
                'quiz_done': ESPUser.objects.filter(qo).distinct(),
            }

    def teacherDesc(self):
        return {
            'quiz_done': """Teachers who have completed the teacher logistics quiz.""",
        }

    # Per-user info
    def isCompleted(self):
        """Return true if user has filled out the teacher quiz."""
        return self.controller.isCompleted(self.user)

    # Views
    @main_call
    @needs_teacher
    @meets_deadline('/Quiz')
    def quiz(self, request, tl, one, two, module, extra, prog):
    
        custom_form_id = Tag.getProgramTag('quiz_form_id', prog, None)
        if custom_form_id:
            cf = Form.objects.get(id=int(custom_form_id))
        else:
            raise ESPError('Cannot find an appropriate form for the quiz.  Please ask your administrator to create a form and set the quiz_form_id Tag.')
        
        form_wizard = FormHandler(cf, request, self.user).getWizard()
        form_class = form_wizard.form_list[0]
    
        if request.method == 'POST':
            form = form_class(request.POST)
            if form.is_valid():
                self.controller.markCompleted(self.user)
                return self.goToCore(tl)
        else:
            form = form_class()
            
        return render_to_response(self.baseDir()+'quiz.html', request, (prog, tl), {'prog':prog, 'form': form})

    class Meta:
        abstract = True

