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
from esp.users.models import Record, ESPUser, Permission
from esp.program.models import PhaseZeroRecord
from esp.program.modules.forms.phasezero import LotteryNumberForm, SubmitForm

import random, copy, datetime, json
from django.contrib.auth.models import Group
from esp.tagdict.models import Tag

class StudentRegPhaseZeroManage(ProgramModuleObj):
    def isCompleted(self):
        return get_current_request().user.canPassPhaseZero(self.program)

    @classmethod
    def module_properties(cls):
        return {
            "module_type": "manage",
            'required': False,
            'admin_title': 'Manage Student Registration Phase Zero',
            'link_title': 'Manage Phase Zero',
        }

    def lottery(self, prog, role):
        #run lottery. Get grade caps and process student data in PhaseZeroRecords
        grade_caps = prog._grade_caps()
        sibgroups = {}

        for entry in PhaseZeroRecord.objects.filter(program=prog):
            group_number = entry.lottery_number
            user = entry.user
            user_grade = entry.user.getGrade(prog)
            lottery_id = entry.id

            if group_number not in sibgroups.keys():
                sibgroups[group_number] = [(user, user_grade, lottery_id)]
            else:
                sibgroups[group_number].append((user, user_grade, lottery_id))

        for number in sibgroups:
            if len(sibgroups[number]) > 4:
                for user in sibgroups[number]:
                    sibgroups[user[2]] = [user]

        ###############################################################################
        # The lottery algorithm is run, with randomization and processing in order.
        # If any one in the group doesn't get in (due to cap size), no one in that group gets in.

        groups = sibgroups.keys()
        random.shuffle(groups)

        counts = {key:0 for key in grade_caps}
        winners = Group(name=role)

        for i in groups:
            sibs = sibgroups[i]
            newcounts = copy.copy(counts)
            for j in sibs:
                newcounts[j[1]] += 1

            cpass = True
            for c in counts.keys():
                if newcounts[c] > grade_caps[c]:
                    cpass = False

            if cpass:
                for user in sibs:
                    winners.add(user[0])    # check syntax
                counts = copy.copy(newcounts)

        ###############################################################################
        # Post lottery, assign permissions to people in the lottery winners group
        # Assign OverridePhaseZero permission and all Student permissions

        Permission(permission_type='OverridePhaseZero', role=winners, start_date=datetime.datetime.now(), program=prog)
        Permission(permission_type='Student/All', role=winners, start_date=datetime.datetime.now(), program=prog)
        
        # Add tag to indicate student lottery has been run
        Tag.setTag('student_lottery_run', prog, True)
 
        return

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
