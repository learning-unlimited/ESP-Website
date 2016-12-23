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
from django.db.models.query import Q

import random, copy, datetime, re
from django.contrib.auth.models import Group
from esp.tagdict.models import Tag

class StudentRegPhaseZero(ProgramModuleObj):
    def students(self, QObject = False):
        q_phasezero = Q(phasezerorecord__program=self.program)

        if QObject:
            retVal = {'phasezero': q_phasezero}
            return retVal

        retVal = {'phasezero': ESPUser.objects.filter(q_phasezero).distinct()}
        return retVal

    def studentDesc(self):
        retVal = {'phasezero': """Students who have entered the Student Lottery."""}
        return retVal

    def isCompleted(self):
        return get_current_request().user.canPassPhaseZero(self.program)

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Registration Phase Zero",
            "link_title": "Student Registration Phase Zero",
            "module_type": "learn",
            "seq": 2,
            "required": True
        }

    @main_call
    @needs_student
    @meets_grade
    def studentregphasezero(self, request, tl, one, two, module, extra, prog):
        """
        Serves the Phase Zero student reg page. The initial page includes a button
        to enter the student lottery. Following entering the lottery, students are
        served a confirmation page and lottery number form (for self-assigning groups).
        """
        context = {}
        context['program'] = prog
        user = request.user
        in_lottery = PhaseZeroRecord.objects.filter(user=user, program=prog).exists()

        op = ''
        join_error = False
        if 'op' in request.POST:
            op = request.POST['op']
        if op == 'join':
            if len(request.POST['student_selected'].strip()) == 0:
                join_error = 'Error - You must select a student\'s username.'
            elif (request.POST['student_selected'] == str(request.user.id)):
                join_error = 'Error - You cannot select yourself!'
            elif not PhaseZeroRecord.objects.filter(user=request.POST['student_selected'], program=prog).exists():
                join_error = 'Error - You can only join a student that is already in the lottery!'

            if join_error:
                form = SubmitForm(program=prog)
                context['form'] = form
                context['join_error'] = join_error
                return render_to_response('program/modules/studentregphasezero/submit.html', request, context)
            #else: join student in lottery

        elif Permission.user_has_perm(user, 'Student/Classes/PhaseZero', program=prog):
            if in_lottery:
                if request.method == 'POST':
                    form = LotteryNumberForm(request.POST, program=prog)
                    if form.is_valid():
                        form.save(user, prog)
                form = LotteryNumberForm(program=prog)
                form.load(request.user, prog)
                context['form'] = form
                context['lottery_number'] = PhaseZeroRecord.objects.filter(user=user, program=prog)[0].lottery_number
                return render_to_response('program/modules/studentregphasezero/confirmation.html', request, context)
            else:
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
            if in_lottery:
                if Tag.getBooleanTag('student_lottery_run', prog, default=False):
                    #Sorry page
                    return render_to_response('program/modules/studentregphasezero/sorry.html', request, context)
                else:
                    #Lottery has not yet been run page
                    return render_to_response('program/modules/studentregphasezero/notyet.html', request, context)
            else:
                #Generic error page
                return render_to_response('errors/program/phasezero_closed.html', request, context)

    @aux_call
    @needs_student
    def studentlookup(self, request, tl, one, two, module, extra, prog, newclass = None):

        # Search for teachers with names that start with search string
        if not 'username' in request.GET or 'username' in request.POST:
            return self.goToCore(tl)

        return StudentRegPhaseZero.studentlookup_logic(request, tl, one, two, module, extra, prog, newclass)

    @staticmethod
    def studentlookup_logic(request, tl, one, two, module, extra, prog, newclass = None):
        limit = 10
        from esp.web.views.json_utils import JsonResponse

        Q_student = Q(groups__name="Student")

        queryset = ESPUser.objects.filter(Q_student)

        if not 'username' in request.GET:
            startswith = request.POST['username']
        else:
            startswith = request.GET['username']

        #   Don't return anything if there's no input.
        if len(startswith) > 0:
            Q_username = Q(username__istartswith=startswith)

            # Isolate user objects
            queryset = queryset.filter(Q_username)[:(limit*10)]
            user_dict = {}
            for user in queryset:
                user_dict[user.id] = user
            users = user_dict.values()

            # Construct combo-box items
            obj_list = [{'username': user.username, 'id': user.id} for user in users]
        else:
            obj_list = []

        return JsonResponse(obj_list)

    class Meta:
        proxy = True
        app_label = 'modules'
