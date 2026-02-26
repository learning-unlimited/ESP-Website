
from __future__ import absolute_import
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from esp.middleware.threadlocalrequest import get_current_request
from esp.program.modules.base import ProgramModuleObj, main_call, needs_student_in_grade, needs_student_in_grade, meets_cap
from esp.program.modules.handlers.programprintables import ProgramPrintables
from esp.program.models import StudentRegistration
from esp.tagdict.models import Tag
from esp.users.models import Record
from esp.utils.latex  import render_to_latex

from datetime import datetime

class StudentCertModule(ProgramModuleObj):
    doc = """Allows students to download a completion certificate
             for the program once the program has ended."""

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Print Completion Certificate",
            "admin_title": "Student Certificate Module",
            "module_type": "learn",
            "required": False,
            "seq": 999999,
            "choosable": 0,
            }

    @main_call
    @needs_student_in_grade
    @meets_cap
    def certificate(self, request, tl, one, two, module, extra, prog):
        if not self.isStep():
            return self.goToCore(tl)

        user = request.user

        if extra:
            file_type = extra.strip()
        else:
            file_type = 'pdf'

        attended = Tag.getProgramTag('student_certificate', prog) == 'class_attendance'
        if attended:
            verbs = ['Attended']
        else:
            verbs = ['Enrolled']

        context = {'user': user, 'prog': prog,
                   'schedule': ProgramPrintables.getTranscript(prog, user, 'latex', verbs, valid_only = (not attended)),
                   'descriptions': ProgramPrintables.getTranscript(prog, user, 'latex_desc', verbs, valid_only = (not attended))}

        return render_to_latex('program/modules/programprintables/completion_certificate.tex', context, file_type)

    def isStep(self):
        if hasattr(self, 'user'):
            user = self.user
        else:
            request = get_current_request()
            user = request.user
        cert_tag = Tag.getProgramTag('student_certificate', self.program)
        slots = self.program.getTimeSlots()
        if slots and datetime.now() > max(slots).end:
            if cert_tag == 'all':
                return True
            elif cert_tag == 'program_attendance':
                return Record.user_completed(user, "attended", self.program)
            elif cert_tag == 'class_attendance':
                return StudentRegistration.objects.filter(user = user, section__parent_class__parent_program=self.program, relationship__name = 'Attended').exists()
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
