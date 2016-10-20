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
from esp.program.models import PhaseZeroRecord, getGrade
from esp.program.modules.forms.phasezero import LotteryNumberForm, SubmitForm

import random, copy, datetime, re
from django.contrib.auth.models import Group
from esp.tagdict.models import Tag

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

        def RepresentInt(x):
            try:
                int(x)
                return True
            except ValueError:
                return False

        sibgroups = {}
        indiv = {}

        # Get grade caps and process student data in PhaseZeroRecords
        grade_caps_tag = Tag.getProgramTag('program_size_by_grade', prog)
        grade_caps_tag_split = [x for x in re.split('(\d+)', grade_caps_tag) if RepresentInt(x)]
        grade_caps = {grade_caps_tag_split[2*i]:int(grade_caps_tag_split[2*i+1]) for i in range(len(grade_caps_tag_split)/2)}

        # Can you check if these are the correct calls to methods/parameters?
        for entry in PhaseZeroRecord.objects:
            group_number = entry.lottery_number
            username = entry.user
            user_grade = entry.user.getGrade(prog)

            indiv[username] = (group_number, user_grade)
            if group_number not in sibgroups.keys():
                sibgroups[group_number] = [(username, user_grade)]
            else:
                sibgroups[group_number].append((username, user_grade))

        ###############################################################################
        # The lottery algorithm is run, with randomization and processing in order.
        # If any one in the group doesn't get in (due to cap size), no one in that group gets in.

        # not sure if we need to deep copy here; kept as shallow
        groups = sibgroups.keys()
        order = copy.copy(groups)
        random.shuffle(order)

        counts = {key:0 for key in grade_caps}
        winners = Group(name=(str(prog) + ' Winners'))
        waitlist = Group(name=(str(prog) + ' Waitlist'))

        for i in order:
            sibs = sibgroups[i]
            newcounts = copy.copy(counts)
            for j in sibs:
                newcounts[j[1]] += 1

            cpass = True
            for c in counts.keys():
                if newcounts[c] > caps[c]:
                    cpass = False

            if cpass:
                for user in sibs:
                    winners.add(user[0])   # correct syntax??
                counts = copy.copy(newcounts)
            else:
                for user in sibs:
                    waitlist.add(user[0])

        ###############################################################################
        # Post lottery, assign permissions to people in the lottery winners group

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
