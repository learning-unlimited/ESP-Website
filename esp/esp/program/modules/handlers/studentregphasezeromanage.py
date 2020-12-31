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
from esp.program.modules.handlers.bigboardmodule import BigBoardModule

from django.contrib.auth.models import Group
from django.db.models.query import Q

import copy, datetime, json, re

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
            'choosable': 0,
        }

    def lottery(self, prog, role, post):
        messages = []
        winners, _ = Group.objects.get_or_create(name=role)
        students = []

        if post.get('mode') == 'default':
            # Get grade caps
            grade_caps_str = prog.grade_caps()
            if grade_caps_str:
                grade_caps = {int(key[0]): value for key, value in grade_caps_str.iteritems()}
                ###############################################################################
                # The default lottery algorithm is run, with randomization and processing in order.
                # If any one in the group doesn't get in (due to cap size), no one in that group gets in.
                records = PhaseZeroRecord.objects.filter(program=prog).order_by('?')

                counts = {key:0 for key in grade_caps}

                for i in records:
                    sibs = i.user.all()
                    newcounts = copy.copy(counts)
                    for j in sibs:
                        newcounts[j.getGrade(prog)] += 1

                    cpass = not any(newcounts[c] > grade_caps[c] for c in counts)

                    if cpass:
                        students.extend(sibs)
                        counts = newcounts
            else:
                messages.append("<i>program_size_by_grade</i> <a href='/manage/" + prog.getUrlBase() + "/tags'>tag</a> is not set. Lottery not run.")

        elif post.get('mode') == 'manual':
            usernames = filter(None, re.split(r'[;,\s]\s*', post.get('usernames')))

            #check that all usernames are valid
            for username in usernames:
                try:
                    student = ESPUser.objects.get(username=username)
                except (ValueError, ESPUser.DoesNotExist):
                    messages.append("Could not find a user with username " + username)
                    continue
                if student.isStudent():
                    records = PhaseZeroRecord.objects.filter(program=prog, user=student).order_by('time')
                    if records.count() > 0:
                        if post.get('groups'):
                            students.extend(records[0].user.all())
                        else:
                            students.append(student)
                    else:
                        messages.append(username + " is not in the lottery")
                else:
                    messages.append(username + " is not a student")

        ###############################################################################
        # Post lottery, assign permissions to people in the lottery winners group
        # Assign OverridePhaseZero permission and Student/All permissions
        if len(messages) == 0:
            #Add users to winners group once we are sure there were no problems
            winners.user_set.add(*students)
            override_perm = Permission(permission_type='OverridePhaseZero', role=winners, start_date=datetime.datetime.now(), program=prog)
            studentAll_perm = Permission(permission_type='Student/All', role=winners, start_date=datetime.datetime.now(), program=prog)
            override_perm.save()
            studentAll_perm.save()
            # Add tag to indicate student lottery has been run
            Tag.setTag('student_lottery_run', target=prog, value='True')
            messages.append("The student lottery has been run successfully")

        return messages

    @main_call
    @needs_admin
    def phasezero(self, request, tl, one, two, module, extra, prog):
        context = {}
        role = str(prog) + " Winners"
        context['role'] = role
        q_phasezero = Q(phasezerorecord__program=self.program)
        entrants = ESPUser.objects.filter(q_phasezero).distinct()
        context['grade_caps'] = sorted(prog.grade_caps().iteritems())

        recs = PhaseZeroRecord.objects.filter(program=prog).order_by('time')
        timess = [("number of lottery students", [(rec.user.count(), rec.time) for rec in recs], True)]
        timess_data, start = BigBoardModule.make_graph_data(timess)
        context["left_axis_data"] = [{"axis_name": "#", "series_data": timess_data}]
        context["first_hour"] = start

        grades = range(prog.grade_min, prog.grade_max + 1)
        stats = {}
        invalid_grades = set()

        #Calculate grade counts
        for grade in grades:
            stats[grade] = {}
            stats[grade]['in_lottery'] = 0
        for entrant in entrants:
            grade = entrant.getGrade(prog)
            if grade in grades:
                stats[grade]['in_lottery'] += 1
            else:
                # Catch students that somehow don't have a valid grade
                invalid_grades.add(entrant)
                if 'Invalid Grade' not in stats:
                    stats['Invalid Grade'] = {}
                    stats['Invalid Grade']['in_lottery'] = 0
                stats['Invalid Grade']['in_lottery'] += 1

        #Run lottery if requested
        if request.POST:
            if Tag.getBooleanTag('student_lottery_run', prog):
                context['error'] = "You've already run the student lottery!"
            else:
                if "confirm" in request.POST:
                    role = request.POST['rolename']
                    context['role'] = role
                    context['lottery_messages'] = self.lottery(prog, role, request.POST)
                else:
                    context['error'] = "You did not confirm that you would like to run the lottery"

        #If lottery has been run, calculate acceptance stats
        if Tag.getBooleanTag('student_lottery_run', prog):
            for grade in stats:
                stats[grade]['num_accepted'] = stats[grade]['per_accepted'] = 0
            winners = ESPUser.objects.filter(groups__name=role).distinct()
            for winner in winners:
                grade = winner.getGrade(prog)
                if grade in grades:
                    stats[grade]['num_accepted'] += 1
                else:
                    # Catch students that somehow don't have a valid grade
                    invalid_grades.add(winner)
                    if 'Invalid Grade' not in stats:
                        stats['Invalid Grade'] = {}
                        stats['Invalid Grade']['num_accepted'] = 0
                    stats['Invalid Grade']['num_accepted'] += 1
            for grade in stats:
                if stats[grade]['in_lottery'] == 0:
                    stats[grade]['per_accepted'] = "NA"
                else:
                    stats[grade]['per_accepted'] = round(stats[grade]['num_accepted'],1)/stats[grade]['in_lottery']*100
        context['stats'] = stats
        context['invalid_grades'] = invalid_grades
        return render_to_response('program/modules/studentregphasezero/status.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
