
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


class OnSiteCheckinModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "On-Site User Check-In",
            "link_title": "Check-in (check students off for payments and forms)",
            "module_type": "onsite",
            "seq": 1,
            "choosable": 1,
            }

    def updatePaid(self, paid=True):
        """ Close off the student's invoice and, if paid is True, create a receipt showing
        that they have paid all of the money they owe for the program. """
        if not self.hasPaid():
            iac = IndividualAccountingController(self.program, self.student)
            iac.ensure_required_transfers()
            if paid:
                iac.submit_payment(iac.amount_due())

    def create_record(self, event):
        created = False
        if event=="attended":
            if not self.program.isCheckedIn(self.student):
                rec = Record(user=self.student, event="attended", program=self.program)
                rec.save()
                created = True
        else:
            if event=="paid":
                self.updatePaid(True)

            recs, created = Record.objects.get_or_create(user=self.student,
                                                         event=event,
                                                         program=self.program)
        return created

    def delete_record(self, event):
        if event=="attended":
            if self.program.isCheckedIn(self.student):
                rec = Record(user=self.student, event="checked_out", program=self.program)
                rec.save()
        else:
            if event=="paid":
                self.updatePaid(False)

            recs, created = Record.objects.get_or_create(user=self.student,
                                                event=event,
                                                program=self.program)
            recs.delete()
        return True

    def hasAttended(self):
        return Record.user_completed(self.student, "attended",self.program)

    def isAttending(self):
        return self.program.isCheckedIn(self.student)

    def hasPaid(self):
        iac = IndividualAccountingController(self.program, self.student)
        return Record.user_completed(self.student, "paid", self.program) or \
            iac.has_paid(in_full=True)

    def hasMedical(self):
        return Record.user_completed(self.student, "med", self.program)

    def hasLiability(self):
        return Record.user_completed(self.student, "liab", self.program)

    def timeCheckedIn(self):
        u = Record.objects.filter(event="attended",program=self.program, user=self.student).order_by("time")
        return str(u[0].time.strftime("%H:%M %m/%d/%y"))

    def lastCheckedIn(self):
        u = Record.objects.filter(event="attended",program=self.program, user=self.student).order_by("-time")
        return str(u[0].time.strftime("%H:%M %m/%d/%y"))

    def checkinPairs(self):
        recs = Record.objects.filter(program = self.program, user = self.student, event__in=["attended", "checked_out"]).order_by('time')
        pairs = []
        checked_in = False
        ind = 0
        for rec in recs:
            if not checked_in and rec.event == "attended":
                pairs.append([rec])
                checked_in = True
            elif checked_in and rec.event == "checked_out":
                pairs[ind].append(rec)
                checked_in = False
                ind += 1
        return pairs

    @aux_call
    @needs_onsite
    def ajax_status(self, request, tl, one, two, module, extra, prog, context={}):
        students = ESPUser.objects.filter(prog.students(QObjects=True)['attended']).distinct().order_by('id')

        #   Populate some stats
        if 'snippets' in request.GET:
            snippet_list = request.GET['snippets'].split(',')
        else:
            snippet_list = ['grades']

        if 'grades' in snippet_list:
            grade_levels = {}
            for student in students:
                grade = student.getGrade(self.program)
                if grade not in grade_levels:
                    grade_levels[grade] = 0
                grade_levels[grade] += 1
            context['grade_levels'] = [{'grade': key, 'num_students': grade_levels[key]} for key in grade_levels]
        else:
            context['grade_levels'] = None

        if 'times' in snippet_list:
            start_times = {}
            for student in students:
                start_time = student.getFirstClassTime(prog)
                if start_time not in start_times:
                    start_times[start_time] = 0
                start_times[start_time] += 1
            context['start_times'] = [{'time': key, 'num_students': start_times[key]} for key in start_times]
        else:
            context['start_times'] = None

        if 'students' in snippet_list:
            context['students'] = students
        else:
            context['students'] = None

        context['module'] = self

        json_data = {'checkin_status_html': render_to_string(self.baseDir()+'checkinstatus.html', context)}
        return HttpResponse(json.dumps(json_data))


    @main_call
    @needs_onsite
    def rapidcheckin(self, request, tl, one, two, module, extra, prog):
        context = {}
        if request.method == 'POST':
            #   Handle submission of student
            form = StudentSearchForm(request.POST)
            if form.is_valid():
                student = form.cleaned_data['target_user']
                #   Check that this is a student user who is not also teaching (e.g. an admin)
                if student.isStudent() and student not in self.program.teachers()['class_approved']:
                    if not prog.isCheckedIn(student):
                        rec = Record(user=student, event="attended", program=prog)
                        rec.save()
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
        return render_to_response(self.baseDir()+'ajaxcheckin.html', request, context)

    @aux_call
    @needs_onsite
    def barcodecheckin(self, request, tl, one, two, module, extra, prog):
        context = {}
        if request.method == 'POST':
            results = {'not_found': [], 'existing': [], 'new': [], 'not_student': []}
            form = OnsiteBarcodeCheckinForm(request.POST)
            if form.is_valid():
                codes=form.cleaned_data['uids'].split()
                for code in codes:
                    try:
                        student = ESPUser.objects.get(id=code)
                    except (ValueError, ESPUser.DoesNotExist):
                        results['not_found'].append(code)
                        continue

                    if student.isStudent():
                        if prog.isCheckedIn(student):
                            results['existing'].append(code)
                        else:
                            new = Record(user=student, program=prog, event='attended')
                            new.save()
                            results['new'].append(code)
                    else:
                        results['not_student'].append(code)
        else:
            results = {}
            form=OnsiteBarcodeCheckinForm()
        context['module'] = self
        context['form'] = form
        context['results'] = results
        return render_to_response(self.baseDir()+'barcodecheckin.html', request, context)

    @aux_call
    @needs_onsite
    def ajaxbarcodecheckin(self, request, tl, one, two, module, extra, prog):
        """
        POST to this view to check-in a student with a user ID.
        POST data:
          'code':          The student's ID.
        """
        json_data = {}
        if request.method == 'POST' and 'code' in request.POST:
            code = request.POST['code']
            students = ESPUser.objects.filter(id=code)
            if not students.exists():
                json_data['message'] = '%s is not a user!' % code
            else:
                student = students[0]
                info_string = student.name() + " (" + str(code) + ")"
                if student.isStudent():
                    if prog.isCheckedIn(student):
                        json_data['message'] = '%s is already checked in!' % info_string
                    else:
                        new = Record(user=student, program=prog, event='attended')
                        new.save()
                        json_data['message'] = '%s is now checked in!' % info_string
                else:
                    json_data['message'] = '%s is not a student!' % info_string
        return HttpResponse(json.dumps(json_data), content_type='text/json')

    @aux_call
    @needs_onsite
    def checkin(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST' and 'userid' in request.POST:
            error = False
            message = None
            user = ESPUser.objects.filter(id = request.POST['userid']).first()
            if user:
                self.student = user
                for key in ['attended','paid','liab','med']:
                    if key in request.POST:
                        self.create_record(key)
                    else:
                        self.delete_record(key)
                if "undocheckin" in request.POST:
                    Record.objects.filter(event="attended",program=self.program, user=self.student).order_by("-time")[0].delete()
                if "undocheckout" in request.POST:
                    Record.objects.filter(event="checked_out",program=self.program, user=self.student).order_by("-time")[0].delete()
                message = "Check-in updated for " + user.username
            else:
                error = True

            context = {'error': error, 'message': message}
            return render_to_response('users/usersearch.html', request, context)

        else:
            user, found = search_for_user(request, self.program.students_union())
            if not found:
                return user

            self.student = user
            return render_to_response(self.baseDir()+'checkin.html', request, {'module': self, 'program': prog})


    class Meta:
        proxy = True
        app_label = 'modules'
