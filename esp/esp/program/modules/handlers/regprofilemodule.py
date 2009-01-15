
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
from esp.program.models import RegistrationProfile
from esp.users.models   import ESPUser, User
from django.db.models.query import Q
from django.contrib.auth.decorators import login_required

# reg profile module
class RegProfileModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Update Your Profile",
            "module_type": "teach",
            "seq": 1,
            "required": True
            }

    def students(self, QObject = False):
        if QObject:
            return {'student_profile': self.getQForUser(Q(registrationprofile__program = self.program, registrationprofile__student_info__isnull = False))
                    }
        students = User.objects.filter(registrationprofile__program = self.program, registrationprofile__student_info__isnull = False).distinct()
        return {'student_profile': students }

    def studentDesc(self):
        return {'student_profile': """Students who have completed the profile."""}

    def teachers(self, QObject = False):
        if QObject:
            return {'teacher_profile': self.getQForUser(Q(registrationprofile__program = self.program) & \
                               Q(registrationprofile__teacher_info__isnull = False))}
        teachers = User.objects.filter(registrationprofile__program = self.program, registrationprofile__teacher_info__isnull = False).distinct()
        return {'teacher_profile': teachers }

    def teacherDesc(self):
        return {'teacher_profile': """Teachers who have completed the profile."""}

    @main_call
    @login_required
    def profile(self, request, tl, one, two, module, extra, prog):
    	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """

        from esp.web.views.myesp import profile_editor
        role = {'teach': 'teacher','learn': 'student'}[tl]

        #   Reset e-mail address for program registrations.
        if prog is None:
            regProf = RegistrationProfile.getLastProfile(request.user)
        else:
            regProf = RegistrationProfile.getLastForProgram(request.user, prog)
        if regProf.id is None:
            regProf = RegistrationProfile.getLastProfile(request.user)

        # aseering 8/20/2007: It is possible for a user to not have a
        # contact_user associated with their registration profile.
        # Deal nicely with this.
        if hasattr(regProf.contact_user, 'e_mail'):
            regProf.contact_user.e_mail = ''
            regProf.contact_user.save()

	response = profile_editor(request, prog, False, role)
	if response == True:
            return self.goToCore(tl)
	return response

    def isCompleted(self):
        regProf = RegistrationProfile.getLastForProgram(self.user, self.program)
        return regProf.id is not None


