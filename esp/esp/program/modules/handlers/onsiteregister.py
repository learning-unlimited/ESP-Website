
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.utils.web import render_to_response
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from esp.users.models    import ESPUser, Record, ContactInfo, StudentInfo, K12School
from django.http import HttpResponseRedirect
from esp.program.models import RegistrationProfile
from esp.program.modules.forms.onsite import OnSiteRegForm
from esp.accounting.controllers import IndividualAccountingController

class OnSiteRegister(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Onsite New Registration",
            "link_title": "New Student Registration",
            "module_type": "onsite",
            "seq": 30,
            "choosable": 1,
            }


    @main_call
    @needs_onsite
    def onsite_create(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            form = OnSiteRegForm(request.POST)

            if form.is_valid():
                new_data = form.cleaned_data
                username = ESPUser.get_unused_username(new_data['first_name'], new_data['last_name'])
                new_user = ESPUser.objects.create_user(username = username,
                                first_name = new_data['first_name'],
                                last_name  = new_data['last_name'],
                                email      = new_data['email'])

                self.user = new_user

                regProf = RegistrationProfile.getLastForProgram(new_user,
                                                                self.program)
                contact_user = ContactInfo(first_name = new_user.first_name,
                                           last_name  = new_user.last_name,
                                           e_mail     = new_user.email,
                                           user       = new_user)
                contact_user.save()
                regProf.contact_user = contact_user

                student_info = StudentInfo(user = new_user, graduation_year = ESPUser.YOGFromGrade(new_data['grade'], ESPUser.program_schoolyear(self.program)))

                try:
                    if isinstance(new_data['k12school'], K12School):
                        student_info.k12school = new_data['k12school']
                    else:
                        if isinstance(new_data['k12school'], int):
                            student_info.k12school = K12School.objects.get(id=int(new_data['k12school']))
                        else:
                            student_info.k12school = K12School.objects.filter(name__icontains=new_data['k12school'])[0]
                except:
                    student_info.k12school = None
                student_info.school = new_data['school'] if not student_info.k12school else student_info.k12school.name

                student_info.save()
                regProf.student_info = student_info

                regProf.save()

                if new_data['paid']:
                    Record.createBit('paid', self.program, self.user)
                    IndividualAccountingController.updatePaid(self.program, self.user, True)
                else:
                    IndividualAccountingController.updatePaid(self.program, self.user, False)

                Record.createBit('Attended', self.program, self.user)

                if new_data['medical']:
                    Record.createBit('Med', self.program, self.user)

                if new_data['liability']:
                    Record.createBit('Liab', self.program, self.user)

                Record.createBit('OnSite', self.program, self.user)


                new_user.groups.add(Group.objects.get(name="Student"))

                new_user.recoverPassword()

                return render_to_response(self.baseDir()+'reg_success.html', request, {
                    'student': new_user,
                    'retUrl': '/onsite/%s/classchange_grid?student_id=%s' % (self.program.getUrlBase(), new_user.id)
                    })

        else:
            form = OnSiteRegForm()

        return render_to_response(self.baseDir()+'reg_info.html', request, {'form':form})

    class Meta:
        proxy = True
        app_label = 'modules'
