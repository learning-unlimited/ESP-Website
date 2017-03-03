__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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

from esp.utils.web import render_to_response
from esp.middleware.threadlocalrequest import get_current_request
from esp.program.modules.base import ProgramModuleObj, main_call, aux_call, meets_deadline, needs_student, meets_grade, meets_cap, no_auth, needs_admin
from esp.users.models import Record, ESPUser
from esp.program.models import PhaseZeroRecord
from esp.program.modules.forms.phasezero import LotteryNumberForm, SubmitForm

class StudentRegPhaseZero(ProgramModuleObj):
    def isCompleted(self):
        return get_current_request().user.canPassPhaseZero(self.program)

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Student Registration Phase Zero",
            "link_title": "Student Registration Phase Zero",
            "module_type": "learn",
            "seq": 0,
            "required": True
        }, {
            "module_type": "manage",
            'required': False,
            'admin_title': 'Manage Student Registration Phase Zero',
            'link_title': 'Manage Phase Zero',
        } ]

    def lottery(self, prog, role):
        #run lottery
        return

    @main_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/PhaseZero')
    def studentregphasezero(self, request, tl, one, two, module, extra, prog):
        """
        Serves the Phase Zero student reg page. The initial page includes a button
        to enter the student lottery. Following entering the lottery, students are
        served a confirmation page and lottery number form (for self-assigning groups).
        """
        context = {}
        user = request.user

        context['program'] = prog

        if not(PhaseZeroRecord.objects.filter(user=user, program=prog).exists()):
            if request.method == 'POST':
                form = SubmitForm(request.POST, program=prog)
                if form.is_valid():
                    form.save(user, prog)
                form = LotteryNumberForm(program=prog)
                form.load(request.user, prog)
                context['lottery_number'] = PhaseZeroRecord.objects.filter(user=user, program=prog)[0].lottery_number
                context['form'] = form
                return render_to_response('program/modules/studentregphasezero/confirmation.html', request, context)
            else:
                form = SubmitForm(program=prog)
                context['form'] = form
                return render_to_response('program/modules/studentregphasezero/submit.html', request, context)
        else:
            if request.method == 'POST':
                form = LotteryNumberForm(request.POST, program=prog)
                if form.is_valid():
                    form.save(user, prog)
            form = LotteryNumberForm(program=prog)
            form.load(request.user, prog)
            context['form'] = form
            context['lottery_number'] = PhaseZeroRecord.objects.filter(user=user, program=prog)[0].lottery_number
            return render_to_response('program/modules/studentregphasezero/confirmation.html', request, context)

    @main_call
    @needs_admin
    def phasezero(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['role'] = str(prog) + " Winners"
        context['recs'] = PhaseZeroRecord.objects.filter(program=prog)
        context['nrecs'] = len(context['recs'])
        if request.POST:
            role = request.POST['rolename']
            context['role'] = role
            if "confirm" in request.POST:
                self.lottery(prog, role)
                context['success'] = "The student lottery has been run successfully."
            else:
                context['error'] = "You did not confirm that you would like to run the lottery"
        return render_to_response('program/modules/studentregphasezero/status.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
