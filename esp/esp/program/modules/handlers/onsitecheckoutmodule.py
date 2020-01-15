
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

from esp.program.modules.forms.onsite import OnsiteBarcodeCheckinForm
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.accounting.controllers import IndividualAccountingController
from esp.utils.web import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.forms.generic_search_form import StudentSearchForm
from esp.users.models    import ESPUser, User, Record
from django              import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string, select_template
from esp.users.views    import search_for_user

import json


class OnSiteCheckoutModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "On-Site User Check-Out",
            "link_title": "Check-out Students",
            "module_type": "onsite",
            "seq": 1
            }

    def create_record(self, event):
        if event=="paid":
            self.updatePaid(True)

        recs, created = Record.objects.get_or_create(user=self.student,
                                                     event=event,
                                                     program=self.program)
        return created

    def delete_record(self, event):
        if event=="paid":
            self.updatePaid(False)

        recs, created = Record.objects.get_or_create(user=self.student,
                                            event=event,
                                            program=self.program)
        recs.delete()
        return True

    def hasAttended(self):
        return Record.user_completed(self.student, "attended",self.program)

    def timeCheckedIn(self):
        u = Record.objects.filter(event="attended",program=self.program, user=self.student).order_by("time")
        return str(u[0].time.strftime("%H:%M %d/%m/%y"))

    @main_call
    @needs_onsite
    def checkout(self, request, tl, one, two, module, extra, prog):
        context = {}
        if request.method == 'POST':
            #   Handle submission of student
            form = StudentSearchForm(request.POST)
            if form.is_valid():
                student = form.cleaned_data['target_user']
                #   Check that this is a student user who is not also teaching (e.g. an admin)
                if student.isStudent() and student not in self.program.teachers()['class_approved']:
                    recs = Record.objects.filter(user=student, event="attended", program=prog)
                    if not recs.exists():
                        rec, created = Record.objects.get_or_create(user=student, event="attended", program=prog)
                    context['message'] = '%s %s marked as attended.' % (student.first_name, student.last_name)
                    if request.is_ajax():
                        return self.ajax_status(request, tl, one, two, module, extra, prog, context)
                else:
                    context['message'] = '%s %s is not a student and has not been checked in' % (student.first_name, student.last_name)
                    if request.is_ajax():
                        return self.ajax_status(request, tl, one, two, module, extra, prog, context)
                form = StudentSearchForm(initial={'target_user': student.id})
        else:
            form = StudentSearchForm()

        context['module'] = self
        context['form'] = form
        return render_to_response(self.baseDir()+'checkout.html', request, context)


    class Meta:
        proxy = True
        app_label = 'modules'
