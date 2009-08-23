
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
from esp.users.models    import ESPUser, UserBit, User, ContactInfo, StudentInfo
from esp.datatree.models import *
from django.http import HttpResponseRedirect
from esp.program.models import RegistrationProfile
from esp.program.modules.forms.onsite import OnSiteRegForm
from esp.accounting_docs.models   import Document


class OnSiteRegister(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Onsite New Registration",
            "link_title": "New Student Registration",
            "module_type": "onsite",
            "seq": 30
            }

    def updatePaid(self, paid=True):
        """ Create an invoice for the student and, if paid is True, create a receipt showing
        that they have paid all of the money they owe for the program. """
        li_types = self.program.getLineItemTypes(self.student)
        doc = Document.get_invoice(self.student, self.program_anchor_cached(), li_types)
        Document.prepare_onsite(self.student, doc.locator)
        if paid:
            Document.receive_onsite(self.student, doc.locator)

    def createBit(self, extension):
        if extension == 'Paid':
            self.updatePaid(True)
            
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
    def onsite_create(self, request, tl, one, two, module, extra, prog):
	if request.method == 'POST':
	    form = OnSiteRegForm(request.POST)
            
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

                new_user.save()

                regProf = RegistrationProfile.getLastForProgram(new_user,
                                                                self.program)
                contact_user = ContactInfo(first_name = new_user.first_name,
                                           last_name  = new_user.last_name,
                                           e_mail     = new_user.email,
                                           user       = new_user)
                contact_user.save()
                regProf.contact_user = contact_user

                student_info = StudentInfo(user = new_user, graduation_year = ESPUser.YOGFromGrade(new_data['grade']))
                student_info.save()
                regProf.student_info = student_info

                regProf.save()

                new_user = ESPUser(new_user)
                
                if new_data['paid']:
                    self.createBit('Paid')
                    self.updatePaid(True)
                else:
                    self.updatePaid(False)

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

                new_user.recoverPassword()
                
                return render_to_response(self.baseDir()+'reg_success.html', request, (prog, tl), {'student': new_user, 'retUrl': '/onsite/%s/schedule_students?extra=285&op=usersearch&userid=%s' % \
                                                                                                   (self.program.getUrlBase(), new_user.id)})

        else:
	    form = OnSiteRegForm()

	return render_to_response(self.baseDir()+'reg_info.html', request, (prog, tl), {'form':form})
        
 
