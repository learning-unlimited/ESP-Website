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
from esp.dbmail.models import send_mail
from esp.tagdict.models import Tag
from esp.web.views.json_utils import JsonResponse

from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.contrib.auth.models import Group
from django.db.models.query import Q

import random, copy, datetime, re

class StudentRegPhaseZero(ProgramModuleObj):
    def students(self, QObject = False):
        q_phasezero = Q(phasezerorecord__program=self.program)

        if QObject:
            return {'phasezero': q_phasezero}

        return {'phasezero': ESPUser.objects.filter(q_phasezero).distinct()}

    def studentDesc(self):
        return {'phasezero': """Students who have entered the Student Lottery"""}

    def isCompleted(self):
        return get_current_request().user.can_skip_phase_zero(self.program)

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Registration Phase Zero",
            "link_title": "Student Registration Phase Zero",
            "module_type": "learn",
            "seq": 2,
            "required": True,
            "choosable": 0,
        }

    @main_call
    @needs_student
    @meets_grade
    def studentregphasezero(self, request, tl, one, two, module, extra, prog):
        """
        Serves the Phase Zero student reg page. The initial page includes a button
        to enter the student lottery. Following entering the lottery, students are
        served a confirmation page.
        """
        context = {}
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        user = request.user

        if user.can_skip_phase_zero(self.program):
            #Student has permission to skip this module, redirect to main student reg page
            #This includes students that won the lottery
            return HttpResponseRedirect('/learn/%s/studentreg' % prog.getUrlBase())
        else:
            #Student must win the lottery to progress
            #Figure out if lottery is open/closed, if it has already been run, and if student has entered yet
            lottery_perm = Permission.user_has_perm(user, 'Student/Classes/PhaseZero', program=prog)
            in_lottery = PhaseZeroRecord.objects.filter(user=user, program=prog).exists()
            lottery_run = Tag.getBooleanTag('student_lottery_run', prog)
            num_allowed_users = int(Tag.getProgramTag("student_lottery_group_max", prog))
            context['lottery_perm'] = lottery_perm
            context['lottery_run'] = lottery_run
            context['num_allowed_users'] = num_allowed_users

            if not in_lottery:
                if lottery_run:
                    #Lottery has been run, student did not enter
                    #Show generic phase zero closed page ("you didn't enter")
                    return render_to_response('errors/program/phasezero_closed.html', request, context)
                elif not lottery_perm:
                    #Lottery hasn't opened yet
                    #Show generic deadline error page
                    context['moduleObj'] = self
                    context['extension'] = ('the deadline Student/Classes/PhaseZero was')
                    return render_to_response('errors/program/deadline-learn.html', request, context)
                elif request.method == 'POST':
                    #Lottery is open, student just entered
                    #Send confirmation email, then show confirmation page below
                    form = SubmitForm(request.POST, program=prog)
                    if form.is_valid():
                        form.save(user, prog)
                        self.send_confirmation_email(user)
                        in_lottery = True

            if in_lottery:
                #Lottery is open or closed, student has entered
                #This includes students that didn't win after the lottery is run
                #Show confirmation page with details about lottery group and lottery status
                context['lottery_group'] = PhaseZeroRecord.objects.get(user=user, program=prog)
                context['lottery_size'] = context['lottery_group'].user.count()
                return render_to_response('program/modules/studentregphasezero/confirmation.html', request, context)
            else:
                #Lottery is open, student has not entered
                #Show lottery enrollment page
                form = SubmitForm(program=prog)
                context['form'] = form
                return render_to_response('program/modules/studentregphasezero/submit.html', request, context)

    @aux_call
    @needs_student
    def joingroup(self, request, tl, one, two, module, extra, prog, newclass = None):
        context = {}
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        user = request.user
        lottery_perm = Permission.user_has_perm(user, 'Student/Classes/PhaseZero', program=prog)
        in_lottery = PhaseZeroRecord.objects.filter(user=user, program=prog).exists()
        lottery_run = Tag.getBooleanTag('student_lottery_run', prog)
        num_allowed_users = int(Tag.getProgramTag("student_lottery_group_max", prog))
        context['lottery_perm'] = lottery_perm
        context['lottery_run'] = lottery_run
        context['num_allowed_users'] = num_allowed_users

        join_error = False
        if len(request.POST.get('student_selected', '').strip()) == 0:
            join_error = 'Error - You must select a student\'s username.'

        else:
            join_user = request.POST['student_selected']
            try:
                group = PhaseZeroRecord.objects.get(user=join_user, program=prog)
            except PhaseZeroRecord.DoesNotExist:
                join_error = 'Error - That student is not in a lottery group.'
            else:
                if in_lottery:
                    old_group = PhaseZeroRecord.objects.get(user=user, program=prog)
                num_users = group.user.count()
                if join_user == str(user.id):
                    join_error = 'Error - You can not select yourself.'
                elif in_lottery and old_group==group:
                    join_error = 'Error - You are already in this lottery group.'
                elif num_users < num_allowed_users:
                    group.user.add(user)
                    group.save()
                    self.send_confirmation_email(user)
                    if in_lottery:
                        old_group.user.remove(user)
                        old_group.save()
                        if not old_group.user.exists():
                            old_group.delete()
                else:
                    join_error = 'Error - This group already contains the maximum number of students (%s).' % (num_allowed_users)

        context['join_error'] = join_error
        if join_error and not in_lottery:
            form = SubmitForm(program=prog)
            context['form'] = form
            return render_to_response('program/modules/studentregphasezero/submit.html', request, context)

        else:
            context['lottery_group'] = PhaseZeroRecord.objects.get(user=user, program=prog)
            context['lottery_size'] = context['lottery_group'].user.count()
            return render_to_response('program/modules/studentregphasezero/confirmation.html', request, context)

    @aux_call
    @needs_student
    def studentlookup(self, request, tl, one, two, module, extra, prog, newclass = None):

        # Search for students with names that start with search string
        if not 'username' in request.GET or 'username' in request.POST:
            return self.goToCore(tl)

        limit = 10

        queryset = ESPUser.objects.filter(phasezerorecord__program=prog).distinct()

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
            obj_list = [{'username': user.username, 'id': user.id, 'grade': user.getGrade(prog)} for user in users]
        else:
            obj_list = []

        return JsonResponse(obj_list)

    def send_confirmation_email(self, student, note=None):
        email_title = 'Student Lottery Confirmation for %s: %s' % (self.program.niceName(), student.name())
        email_from = '%s Registration System <server@%s>' % (self.program.program_type, settings.EMAIL_HOST_SENDER)
        email_context = {'student': student,
                         'program': self.program,
                         'curtime': datetime.datetime.now(),
                         'note': note,
                         'DEFAULT_HOST': settings.DEFAULT_HOST}
        email_contents = render_to_string('program/modules/studentregphasezero/confirmation_email.txt', email_context)
        email_to = ['%s <%s>' % (student.name(), student.email)]
        send_mail(email_title, email_contents, email_from, email_to, False)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
