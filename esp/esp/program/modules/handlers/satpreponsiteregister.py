
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import *
from django.http import HttpResponseRedirect
from esp.program.models import SATPrepRegInfo
from esp.program.modules.forms.onsite import OnSiteSATPrepRegForm



class SATPrepOnSiteRegister(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "SATPrep On-Site User Creation",
            "module_type": "onsite",
            "seq": 10
            }

    def createBit(self, extension):
        verb = GetNode('V/Flags/Registration/'+extension)
        ub = UserBit.objects.filter(user = self.student,
                                    verb = verb,
                                    qsc  = self.program_anchor_cached())
        if len(ub) > 0:
            return False

        ub = UserBit()
        ub.verb = verb
        ub.qsc  = self.program_anchor_cached()
        ub.user = self.student
        ub.recursive = False
        ub.save()
        return True

    @main_call
    @needs_onsite
    def satprep_create(self, request, tl, one, two, module, extra, prog):
	if request.method == 'POST':
            form = OnSiteSATPrepRegForm(request.POST)
            
            if form.is_valid():
                new_data = form.cleaned_data
                username = base_uname = (new_data['first_name'][0]+ \
                                         new_data['last_name']).lower()
                if User.objects.filter(username = username).count() > 0:
                    i = 2
                    username = base_uname + str(i)
                    while User.objects.filter(username = username).count() > 0:
                        i += 1
                        username = base_uname + str(i)
                new_user = User(username = username,
                                first_name = new_data['first_name'],
                                last_name  = new_data['last_name'],
                                email      = new_data['email'],
                                is_staff   = False,
                                is_superuser = False)
                new_user.save()

                self.student = new_user

                new_user = ESPUser(new_user)
                
                new_user.save()
                new_user.recoverPassword()

                #update satprep information
                satprep = SATPrepRegInfo.getLastForProgram(new_user, self.program)
                satprep.old_math_score = new_data['old_math_score']
                satprep.old_verb_score = new_data['old_verb_score']
                satprep.old_writ_score = new_data['old_writ_score']
                satprep.save()

                if new_data['paid']:
                    self.createBit('Paid')

                self.createBit('Attended')

                if new_data['medical']:
                    self.createBit('MedicalFiled')

                if new_data['liability']:
                    self.createBit('LiabilityFiled')

                self.createBit('OnSite')

		v = GetNode( 'V/Flags/UserRole/Student')
		ub = UserBit()
		ub.user = new_user
		ub.recursive = False
		ub.qsc = GetNode('Q')
		ub.verb = v
		ub.save()
                
                new_user = ESPUser(new_user)

                
                return render_to_response(self.baseDir()+'reg_success.html', request, (prog, tl), {'user': new_user})
        
        else:
            form = OnSiteSATPrepRegForm()

	return render_to_response(self.baseDir()+'reg_info.html', request, (prog, tl), {'form':form})
        
 


