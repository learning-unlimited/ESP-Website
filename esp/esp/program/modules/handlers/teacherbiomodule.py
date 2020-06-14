
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.models import TeacherBio
from esp.users.models   import ESPUser, User
from esp.middleware.threadlocalrequest import get_current_request
from django.db.models.query   import Q

# reg profile module
class TeacherBioModule(ProgramModuleObj):
    """ Module for teacher to edit their biography for each program. """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Biography Editor",
            "link_title": "Update your teacher biography",
            "module_type": "teach",
            "seq": -111,
            "choosable": 1,
            }

    def teachers(self, QObject = False):
        if QObject:
            return {'teacher_biographies': Q(teacherbio__program = self.program)}

        teachers = ESPUser.objects.filter(teacherbio__program = self.program).distinct()
        return {'teacher_biographies': teachers }

    def teacherDesc(self):
        return {'teacher_biographies': """Teachers who have completed the biography"""}

    @main_call
    @needs_teacher
    def biography(self, request, tl, one, two, module, extra, prog):
        """ Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """
        from esp.web.views.bio import bio_edit_user_program
        result = bio_edit_user_program(request, request.user, self.program, external=True)

        if result is not True:
            return result

        return self.goToCore(tl)

    def isCompleted(self):
        #   TeacherBio.getLastForProgram() returns a new bio if one already exists.
        #   So, mark this step completed if there is an existing (i.e. non-empty) bio.
        lastBio = TeacherBio.getLastForProgram(get_current_request().user, self.program)
        return ((lastBio.id is not None) and lastBio.bio and lastBio.slugbio)

    class Meta:
        proxy = True
        app_label = 'modules'
