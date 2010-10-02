
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call, meets_deadline
from esp.program.models import RegistrationProfile
from esp.users.models   import ESPUser, User
from django.db.models.query import Q
from django.contrib.auth.decorators import login_required

# reg profile module
class RegProfileModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Student Profile Editor",
            "link_title": "Update Your Profile",
            "module_type": "learn",
            "seq": 1,
            "required": True
        }, {
            "admin_title": "Teacher Profile Editor",
            "link_title": "Update Your Profile",
            "module_type": "teach",
            "seq": 1,
            "required": True
        } ]

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
    @meets_deadline("/Profile")
    def profile(self, request, tl, one, two, module, extra, prog):
    	""" Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """

        from esp.web.views.myesp import profile_editor
        
        #   Check user role.  Some users may have multiple roles; if one of them
        #   is 'student' or 'teacher' then use that to set up the profile.
        #   Otherwise, make a wild guess.
        user_roles = ESPUser(request.user).getUserTypes()
        user_roles = [x.lower() for x in user_roles]
        if 'teacher' in user_roles or 'student' in user_roles:
            role = {'teach': 'teacher','learn': 'student'}[tl]
        else:
            role = user_roles[0]

        # Make sure we are editing the right type of profile
        if role == 'teacher' and not request.user.isTeacher():
            return needs_teacher(self.profile)(self, request, tl, one, two, module, extra)
        if role == 'student' and not request.user.isStudent():
            return needs_student(self.profile)(self, request, tl, one, two, module, extra)

        #   Reset e-mail address for program registrations.
        if prog is None:
            regProf = RegistrationProfile.getLastProfile(request.user)
        else:
            regProf = RegistrationProfile.getLastForProgram(request.user, prog)

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


