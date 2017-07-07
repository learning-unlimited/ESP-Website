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
from esp.program.modules.forms.phasezero import SubmitForm
from esp.tagdict.models import Tag

from django.contrib.auth.models import Group
from django.db.models.query import Q

import copy, datetime, json

class StudentRegPhaseZeroManage(ProgramModuleObj):
    def isCompleted(self):
        return get_current_request().user.can_skip_phase_zero(self.program)

    @classmethod
    def module_properties(cls):
        return {
            "module_type": "manage",
            'required': False,
            'admin_title': 'Manage Student Registration Phase Zero',
            'link_title': 'Manage Phase Zero',
        }

    def lottery(self, prog, role):
        # Run lottery algorithm.
        # Get grade caps
        grade_caps_str = prog.grade_caps()
        grade_caps = {int(key): value for key, value in grade_caps_str.iteritems()}

        #Get lottery records and randomize them
        records = PhaseZeroRecord.objects.filter(program=prog).order_by('?')

        ###############################################################################
        # The lottery algorithm is run, with randomization and processing in order.
        # If any one in the group doesn't get in (due to cap size), no one in that group gets in.
        counts = {key:0 for key in grade_caps}
        winners, _ = Group.objects.get_or_create(name=role)

        for i in records:
            sibs = i.user.all()
            newcounts = counts
            for j in sibs:
                newcounts[j.getGrade(prog)] += 1

            cpass = not any(newcounts[c] > grade_caps[c] for c in counts)

            if cpass:
                winners.users.add(*sibs)
                counts = newcounts

        ###############################################################################
        # Post lottery, assign permissions to people in the lottery winners group
        # Assign OverridePhaseZero permission and Student/All permissions

        override_perm = Permission(permission_type='OverridePhaseZero', role=winners, start_date=datetime.datetime.now(), program=prog)
        studentAll_perm = Permission(permission_type='Student/All', role=winners, start_date=datetime.datetime.now(), program=prog)
        override_perm.save()
        studentAll_perm.save()
        # Add tag to indicate student lottery has been run
        Tag.setTag('student_lottery_run', target=prog, value='True')

        return True

    @main_call
    @needs_admin
    def phasezero(self, request, tl, one, two, module, extra, prog):
        context = {}
        role = str(prog) + " Winners"
        context['role'] = role
        q_phasezero = Q(phasezerorecord__program=self.program)
        entrants = ESPUser.objects.filter(q_phasezero).distinct()
        context['entrants'] = entrants
        context['nentrants'] = len(entrants)

        grades = range(prog.grade_min, prog.grade_max + 1)
        stats = {}

        #Calculate grade counts
        for grade in grades:
            stats[grade] = {}
            stats[grade]['in_lottery'] = 0
        for entrant in entrants:
            stats[entrant.getGrade(prog)]['in_lottery'] += 1

        #Run lottery if requested
        if request.POST:
            if Tag.getBooleanTag('student_lottery_run', prog, default=False):
                context['error'] = "You've already run the student lottery!"
            else:
                if "confirm" in request.POST:
                    if Tag.getProgramTag('program_size_by_grade', prog):
                        role = request.POST['rolename']
                        context['role'] = role
                        self.lottery(prog, role)
                        context['success'] = "The student lottery has been run successfully."
                    else:
                        context['error'] = "You haven't set the grade caps tag yet."
                else:
                    context['error'] = "You did not confirm that you would like to run the lottery"

        #If lottery has been run, calculate acceptance stats
        if Tag.getBooleanTag('student_lottery_run', prog, default=False):
            for grade in grades:
                stats[grade]['num_accepted'] = stats[grade]['per_accepted'] = 0
            q_winners = Q(groups__name=role)
            winners = ESPUser.objects.filter(q_winners).distinct()
            for winner in winners:
                stats[winner.getGrade(prog)]['num_accepted'] += 1
            for grade in grades:
                if stats[grade]['in_lottery'] == 0:
                    stats[grade]['per_accepted'] = "NA"
                else:
                    stats[grade]['per_accepted'] = round(stats[grade]['num_accepted'],1)/stats[grade]['in_lottery']*100
        context['stats'] = stats
        return render_to_response('program/modules/studentregphasezero/status.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
