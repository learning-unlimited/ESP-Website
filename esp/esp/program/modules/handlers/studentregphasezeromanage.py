from __future__ import absolute_import
from __future__ import division
import six
from six.moves import range
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
from esp.program.modules.base import ProgramModuleObj, main_call, needs_admin
from esp.users.models import ESPUser, Permission
from esp.program.models import PhaseZeroRecord
from esp.tagdict.models import Tag
from esp.program.modules.handlers.bigboardmodule import BigBoardModule

from django.contrib.auth.models import Group
from django.db.models.query import Q

import copy, datetime, re

class StudentRegPhaseZeroManage(ProgramModuleObj):
    doc = """Track registration for the student lottery and/or run the student lottery."""

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
        messages = {'success':[], 'error': []}
        winners, _ = Group.objects.get_or_create(name=role)
        students = []

        if post.get('mode') == 'default':
            # Get grade caps
            grade_caps = prog.grade_caps()
            if grade_caps:
                ###############################################################################
                # The default lottery algorithm is run, with randomization and processing in order.
                # If any one in the group doesn't get in (due to cap size), no one in that group gets in.
                records = PhaseZeroRecord.objects.filter(program=prog).order_by('?')

                counts = {key:0 for key in grade_caps}

                for i in records:
                    sibs = i.user.all()
                    newcounts = copy.copy(counts)
                    for j in sibs:
                        grade = j.getGrade(prog)
                        grade_keys = [key for key in grade_caps if grade in key]
                        if len(grade_keys) == 1:
                            newcounts[grade_keys[0]] += 1
                        elif len(grade_keys) == 0:
                            messages['error'].append("The <i>program_size_by_grade</i> <a href='/manage/" + prog.getUrlBase() + "/tags/learn'>tag</a> does not include grade %i. Lottery not run." % (grade))
                            break
                        else:
                            messages['error'].append("The <i>program_size_by_grade</i> <a href='/manage/" + prog.getUrlBase() + "/tags/learn'>tag</a> includes grade %i multiple times. Lottery not run." % (grade))
                            break

                    cpass = not any(newcounts[c] > grade_caps[c] for c in counts)

                    if cpass:
                        students.extend(sibs)
                        counts = newcounts
            else:
                messages['error'].append("<i>program_size_by_grade</i> <a href='/manage/" + prog.getUrlBase() + "/tags'>tag</a> is not set. Lottery not run.")

        elif post.get('mode') == 'manual':
            usernames = [_f for _f in re.split(r'[;,\s]\s*', post.get('usernames')) if _f]

            # check that all usernames are valid
            for username in usernames:
                try:
                    student = ESPUser.objects.get(username=username)
                except (ValueError, ESPUser.DoesNotExist):
                    messages['error'].append("Could not find a user with username " + username)
                    continue
                if student.isStudent():
                    records = PhaseZeroRecord.objects.filter(program=prog, user=student).order_by('time')
                    if records.count() > 0:
                        if post.get('groups'):
                            students.extend(records[0].user.all())
                        else:
                            students.append(student)
                    else:
                        messages['error'].append(username + " is not in the lottery")
                else:
                    messages['error'].append(username + " is not a student")

        else:
            messages['error'].append("Lottery mode " + post.get('mode') + " is not supported")

        ###############################################################################
        # Post lottery, assign permissions to people in the lottery winners group
        # Assign OverridePhaseZero permission and Student/All permissions
        if len(messages['error']) == 0:
            # Add users to winners group once we are sure there were no problems
            winners.user_set.add(*students)
            override_perm = Permission(permission_type='OverridePhaseZero', role=winners, start_date=datetime.datetime.now(), program=prog)
            override_perm.save()
            if 'perms' in post:
                studentAll_perm = Permission(permission_type='Student/All', role=winners, start_date=datetime.datetime.now(), program=prog)
                studentAll_perm.save()
            # Add tag to indicate student lottery has been run
            Tag.setTag('student_lottery_run', target=prog, value='True')
            messages['success'].append("The student lottery has been run successfully")

        return messages

    @main_call
    @needs_admin
    def phasezero(self, request, tl, one, two, module, extra, prog):
        context = {}
        role = str(prog) + " Winner"
        context['role'] = role
        num_allowed_users = int(Tag.getProgramTag("student_lottery_group_max", prog))

        if request.POST:
            if request.POST.get('mode') == 'addnew':
                add_user = ESPUser.objects.get(id=request.POST['student_selected1'])
                in_lottery = PhaseZeroRecord.objects.filter(user=add_user, program=prog).exists()
                if in_lottery:
                    context['error'] = 'Error - %s is already in the lottery.' % (add_user.name())
                else:
                    rec = PhaseZeroRecord(program=prog)
                    rec.save()
                    rec.user.add(add_user)
                    context['success'] = "%s has been added to the lottery." % (add_user.name())
            elif request.POST.get('mode') == 'addtoexisting':
                add_user = ESPUser.objects.get(id=request.POST['student_selected2'])
                join_user = ESPUser.objects.get(id=request.POST['student_selected3'])
                try:
                    rec = PhaseZeroRecord.objects.get(user=join_user, program=prog)
                except PhaseZeroRecord.DoesNotExist:
                    context['error'] = 'Error - %s is not in an existing lottery group.' % (join_user.name())
                else:
                    in_lottery = PhaseZeroRecord.objects.filter(user=add_user, program=prog).exists()
                    if in_lottery:
                        old_rec = PhaseZeroRecord.objects.get(user=add_user, program=prog)
                    num_users = rec.user.count()
                    if num_users < num_allowed_users:
                        rec.user.add(add_user)
                        rec.save()
                        if in_lottery:
                            old_rec.user.remove(add_user)
                            if not old_rec.user.exists():
                                old_rec.delete()
                            context['success'] = "%s has been moved to a different lottery group." % (add_user.name())
                        context['success'] = "%s has been added to the lottery group." % (add_user.name())
                    else:
                        context['error'] = 'Error - This group already contains the maximum number of students (%s).' % (num_allowed_users)
            elif request.POST.get('mode') == 'remove':
                remove_user = ESPUser.objects.get(id=request.POST['student_selected4'])
                try:
                    rec = PhaseZeroRecord.objects.get(user=remove_user, program=prog)
                except PhaseZeroRecord.DoesNotExist:
                    context['error'] = 'Error - %s is not in the lottery.' % (remove_user.name())
                else:
                    rec.user.remove(remove_user)
                    if not rec.user.exists():
                        rec.delete()
                    context['success'] = "%s has been removed from the lottery." % (remove_user.name())
            elif Tag.getBooleanTag('student_lottery_run', prog):
                if request.POST.get('mode') == 'undo':
                    if "confirm" in request.POST:
                        Group.objects.filter(name=role).delete()
                        Tag.unSetTag('student_lottery_run', prog)
                        context['lottery_succ_msg'] = ["The student lottery has been undone."]
                    else:
                        context['error'] = "You did not confirm that you would like to undo the lottery."
                else:
                    context['error'] = "You've already run the student lottery!"
            # Run lottery if requested
            else:
                if "confirm" in request.POST:
                    role = request.POST['rolename']
                    context['role'] = role
                    messages = self.lottery(prog, role, request.POST)
                    context['lottery_succ_msg'] = messages['success']
                    context['lottery_err_msg'] = messages['error']
                else:
                    context['error'] = "You did not confirm that you would like to run the lottery"

        q_phasezero = Q(phasezerorecord__program=self.program)
        entrants = ESPUser.objects.filter(q_phasezero).distinct()
        context['grade_caps'] = sorted(six.iteritems(prog.grade_caps()))

        recs = PhaseZeroRecord.objects.filter(program=prog).order_by('time')
        timess = [("number of lottery students", [(rec.user.count(), rec.time) for rec in recs], True)]
        timess_data, start = BigBoardModule.make_graph_data(timess)
        context["left_axis_data"] = [{"axis_name": "#", "series_data": timess_data}]
        context["first_hour"] = start

        grades = list(range(prog.grade_min, prog.grade_max + 1))
        stats = {}
        invalid_grades = set()
        # Calculate grade counts
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

        # If lottery has been run, calculate acceptance stats
        if Tag.getBooleanTag('student_lottery_run', prog):
            context['lottery_run'] = True
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
                    stats[grade]['per_accepted'] = round(stats[grade]['num_accepted'], 1)//stats[grade]['in_lottery']*100
        context['stats'] = stats
        context['invalid_grades'] = invalid_grades
        context['num_allowed_users'] = num_allowed_users
        return render_to_response('program/modules/studentregphasezero/status.html', request, context)

    def isStep(self):
        return True

    setup_title = "Set up the 'program size by grade' tag for the student lottery"
    setup_path = "tags/learn"

    def isCompleted(self):
        return Tag.getProgramTag("program_size_by_grade", self.program) is not None

    class Meta:
        proxy = True
        app_label = 'modules'
