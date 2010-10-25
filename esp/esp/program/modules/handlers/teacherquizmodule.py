
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 MIT ESP

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

    def find_errors(self, answer_dict):
        """
        Check quiz answers for errors.

        Not yet ready for programs besides Splash 2010.
        """
        question_numbers = {
            'prog_month': 1,
            'prog_day': 1,
            'photo_exists': 5,
            'call_911': 6,
            'teacher_lunch': 7,
            'check_in': 8,
            'sec1': 3,
            'sec2': 3,
            'sec3': 3,
            'sec4': 3,
            'sec5': 3,
            'sec6': 3,
            
            'reimburse1': 4,
            'reimburse2': 4,
            'reimburse3': 4,
            'reimburse4': 4,

            'security_number': 2,
        }
        correct_answers = {
            'prog_month': '11',
            'photo_exists': 'True',
            'call_911': 'False',
            'teacher_lunch': 'True',
            'check_in': 'True',
        }
        checkboxes = {
            'sec1': True,
            'sec2': False,
            'sec3': True,
            'sec4': False,
            'sec5': True,
            'sec6': True,
            
            'reimburse1': True,
            'reimburse2': False,
            'reimburse3': False,
            'reimburse4': True,
        }
        errors = []
        for key in correct_answers:
            if answer_dict.get(key, '') != correct_answers[key]:
                errors.append(question_numbers[key])
        for key in checkboxes:
            if bool(answer_dict.get(key, False)) != checkboxes[key]:
                errors.append(question_numbers[key])
        # Check the day of the program
        m = self.twoday_pattern.match(answer_dict.get('prog_day'))
        if not m or set(m.groups()) != set(['20','21']):
            errors.append(question_numbers['prog_day'])
        # Check the security number
        ans = answer_dict.get('security_number', '')
        if ''.join([x for x in ans if x.isdigit()]) != '6172534941':
            errors.append(question_numbers['security_number'])
        return set(errors)

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
                'quiz_done': User.objects.filter(qo).distinct(),
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
        if request.method == 'POST':
            errors = self.controller.find_errors(request.POST)
            if not errors:
                self.controller.markCompleted(self.user)
                return self.goToCore(tl)
            return render_to_response(self.baseDir()+'quiz_tryagain.html', request, (prog, tl), {'prog':prog, 'errors': errors})
        else:
            data = {}
            form = None  # SomeFormOrOther(self, initial=data)
            return render_to_response(self.baseDir()+'quiz.html', request, (prog, tl), {'prog':prog, 'form': form})
