
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

from esp.program.modules.module_ext import CreditCardModuleInfo
from esp.program.modules.handlers.creditcardmodule import CreditCardModule
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import GetNode
from django              import forms
from django.http import HttpResponseRedirect
from esp.program.models import SATPrepRegInfo
from esp.users.views    import search_for_user
from esp.money.models   import Transaction


class OnSiteCheckinModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Check-in (check students off for payments and forms)",
            "module_type": "onsite",
            "seq": 1
            }

    def updatePaid(self, paid=True):
        t = Transaction.objects.filter(fbo    = self.student,
                                       anchor = self.program_anchor_cached())
        if t.count() > 0 and not paid:
            for trans in t:
                trans.delete()

        if t.count() == 0 and paid:
            payment_amount = 30.00
            module_list = self.program.getModules()
            module_class = CreditCardModule
            for m in module_list:
                if type(m) == module_class:
                    info = CreditCardModuleInfo.objects.filter(module=m)
                    if info.count() == 1:
                        payment_amount = info[0].base_cost
            
            trans = Transaction(anchor = self.program_anchor_cached(),
                                fbo    = self.student,
                                payer  = self.student,
                                amount = payment_amount,
                                line_item = 'Onsite payment for %s' % self.program.niceName(),
                                executed = True,
                                payment_type_id = 6
                                )
            trans.save()
            

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

    def deleteBit(self, extension):
        if extension == 'Paid':
            self.updatePaid(False)
        verb = GetNode('V/Flags/Registration/'+extension)
        ub = UserBit.objects.filter(user = self.student,
                                    verb = verb,
                                    qsc  = self.program_anchor_cached())
        for userbit in ub:
            userbit.expire()

        return True

    def hasAttended(self):
        verb = GetNode('V/Flags/Registration/Attended')
        return UserBit.UserHasPerms(self.student,
                                    self.program_anchor_cached(),
                                    verb)

    def hasPaid(self):
        verb = GetNode('V/Flags/Registration/Paid')
        return UserBit.UserHasPerms(self.student,
                                    self.program_anchor_cached(),
                                    verb) or \
               Transaction.objects.filter(fbo = self.student,
                                          anchor = self.program_anchor_cached()).count() > 0
    
    def hasMedical(self):
        verb = GetNode('V/Flags/Registration/MedicalFiled')
        return UserBit.UserHasPerms(self.student,
                                    self.program_anchor_cached(),
                                    verb)
    def hasLiability(self):
        verb = GetNode('V/Flags/Registration/LiabilityFiled')
        return UserBit.UserHasPerms(self.student,
                                    self.program_anchor_cached(),
                                    verb)

        

    @main_call
    @needs_onsite
    def checkin(self, request, tl, one, two, module, extra, prog):

        user, found = search_for_user(request, self.program.students_union())
        if not found:
            return user
        
        self.student = user
            
        if request.method == 'POST':
            for key in ['Attended','Paid','LiabilityFiled','MedicalFiled']:
                if request.POST.has_key(key):
                    self.createBit(key)
                else:
                    self.deleteBit(key)
                

            return self.goToCore(tl)

        return render_to_response(self.baseDir()+'checkin.html', request, (prog, tl), {'module': self})

