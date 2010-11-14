
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
  Email: web-team@lists.learningu.org
"""

from esp.program.modules.module_ext import CreditCardModuleInfo
from esp.program.modules.forms.onsite import OnSiteRapidCheckinForm
from esp.program.modules.handlers.creditcardmodule import CreditCardModule
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import *
from django              import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string, select_template
from esp.program.models import SATPrepRegInfo
from esp.users.views    import search_for_user
from esp.accounting_docs.models   import Document

import simplejson as json


class OnSiteCheckinModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "On-Site User Check-In",
            "link_title": "Check-in (check students off for payments and forms)",
            "module_type": "onsite",
            "seq": 1
            }

    def updatePaid(self, paid=True):   
        """ Close off the student's invoice and, if paid is True, create a receipt showing
        that they have paid all of the money they owe for the program. """
        if not self.hasPaid():
            doc = Document.get_invoice(self.student, self.program_anchor_cached())
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
        ps = self.student.paymentStatus(self.program_anchor_cached())
        return UserBit.UserHasPerms(self.student,
                                    self.program_anchor_cached(),
                                    verb) or self.student.has_paid(self.program_anchor_cached())
    
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

    @aux_call
    @needs_onsite
    def ajax_status(self, request, tl, one, two, module, extra, prog, context={}):
        students = ESPUser.objects.filter(prog.students(QObjects=True)['attended']).distinct().order_by('id')
        
        #   Populate some stats
        if 'snippets' in request.GET:
            snippet_list = request.GET['snippets'].split(',')
        else:
            snippet_list = ['grades']
        
        if 'grades' in snippet_list:
            grade_levels = {}
            for student in students:
                grade = student.getGrade()
                if grade not in grade_levels:
                    grade_levels[grade] = 0
                grade_levels[grade] += 1
            context['grade_levels'] = [{'grade': key, 'num_students': grade_levels[key]} for key in grade_levels]
        else:
            context['grade_levels'] = None
            
        if 'times' in snippet_list:
            start_times = {}
            for student in students:
                start_time = student.getFirstClassTime(prog)
                if start_time not in start_times:
                    start_times[start_time] = 0
                start_times[start_time] += 1    
            context['start_times'] = [{'time': key, 'num_students': start_times[key]} for key in start_times]
        else:
            context['start_times'] = None
         
        if 'students' in snippet_list:
            context['students'] = students
        else:
            context['students'] = None
        
        context['module'] = self
        context['program'] = prog
       
        json_data = {'checkin_status_html': render_to_string(self.baseDir()+'checkinstatus.html', context)}
        return HttpResponse(json.dumps(json_data))


    @aux_call
    @needs_onsite
    def rapidcheckin(self, request, tl, one, two, module, extra, prog):
        context = {}
        if request.method == 'POST':
            #   Handle submission of student
            form = OnSiteRapidCheckinForm(request.POST)
            if form.is_valid():
                student = ESPUser(form.cleaned_data['user'])
                existing_bits = UserBit.valid_objects().filter(user=student, qsc=prog.anchor, verb=GetNode('V/Flags/Registration/Attended'))
                if not existing_bits.exists():
                    new_bit, created = UserBit.objects.get_or_create(user=student, qsc=prog.anchor, verb=GetNode('V/Flags/Registration/Attended'))
                context['message'] = '%s %s marked as attended.' % (student.first_name, student.last_name)
                if request.is_ajax():
                    return self.ajax_status(request, tl, one, two, module, extra, prog, context)
        else:
            form = OnSiteRapidCheckinForm()
        
        context['module'] = self
        context['form'] = form
        return render_to_response(self.baseDir()+'ajaxcheckin.html', request, (prog, tl), context)
        

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

