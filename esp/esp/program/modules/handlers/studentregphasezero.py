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
        return {'phasezero': """Students who have entered the Student Lottery."""}

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
            if len(request.POST.get('student_selected', '').strip()) == 0:
                join_error = 'Error - You must select a student\'s username.'

            else:
                join_user = request.POST['student_selected']
                group = PhaseZeroRecord.objects.get(user=join_user, program=prog)
                if in_lottery:
                    old_group = PhaseZeroRecord.objects.get(user=user, program=prog)
                num_users = group.user.count()
                if join_user == str(user.id):
                    join_error = 'Error - You can not select yourself.'
                elif in_lottery and old_group==group:
                    join_error = 'Error - You are already in this lottery group.'
                elif num_users < 4:
                    group.user.add(user)
                    group.save()
                    self.send_confirmation_email(user)
                    if in_lottery:
                        old_group.user.remove(user)
                        old_group.save()
                        if not old_group.user.exists():
                            old_group.delete()
                else:
                    join_error = 'Error - This group already contains the maximum number of students.'

            context['join_error'] = join_error
            if join_error and not in_lottery:
                form = SubmitForm(program=prog)
                context['form'] = form
                return render_to_response('program/modules/studentregphasezero/submit.html', request, context)

            else:
                context['lottery_group'] = PhaseZeroRecord.objects.get(user=user, program=prog)
                context['lottery_size'] = context['lottery_group'].user.count()
                return render_to_response('program/modules/studentregphasezero/confirmation.html', request, context)

        elif Permission.user_has_perm(user, 'Student/Classes/PhaseZero', program=prog):
            if in_lottery:
                context['lottery_group'] = PhaseZeroRecord.objects.get(user=user, program=prog)
                context['lottery_size'] = context['lottery_group'].user.count()
                return render_to_response('program/modules/studentregphasezero/confirmation.html', request, context)
            else:
                if request.method == 'POST':
                    form = SubmitForm(request.POST, program=prog)
                    if form.is_valid():
                        form.save(user, prog)
                    context['lottery_group'] = PhaseZeroRecord.objects.filter(user=user, program=prog)[0]
                    context['lottery_size'] = len(context['lottery_group'].user.all())
                    self.send_confirmation_email(user)
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

        # Search for students with names that start with search string
        if not 'username' in request.GET or 'username' in request.POST:
            return self.goToCore(tl)

        limit = 10

        queryset = ESPUser.objects.filter(Q(phasezerorecord__program=prog)).distinct()

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

    class Meta:
        proxy = True
        app_label = 'modules'
