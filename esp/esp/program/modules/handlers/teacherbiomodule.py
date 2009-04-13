
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.models import TeacherBio
from esp.users.models   import ESPUser, User
from django.db.models.query   import Q

# reg profile module
class TeacherBioModule(ProgramModuleObj):
    """ Module for teacher to edit their biography for each program. """
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Update your teacher biography",
            "module_type": "teach",
            "seq": -111
            }

    def teachers(self, QObject = False):
        if QObject:
            return {'teacher_biographies': self.getQForUser(Q(teacherbio__program = self.program))}
                    
        teachers = User.objects.filter(teacherbio__program = self.program).distinct()
        return {'teacher_biographies': teachers }

    def teacherDesc(self):
        return {'teacher_biographies': """Teachers who have completed the biography."""}

    @main_call
    @needs_teacher
    def biography(self, request, tl, one, two, module, extra, prog):
    	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """
        from esp.web.views.bio import bio_edit_user_program
        result = bio_edit_user_program(request, self.user, self.program, external=True)

        if result is not True:
            return result

        return self.goToCore(tl)

    def isCompleted(self):
        lastBio = TeacherBio.getLastForProgram(self.user, self.program)
        return lastBio.id is not None

