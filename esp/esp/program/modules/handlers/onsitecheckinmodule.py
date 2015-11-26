
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

from esp.program.modules.forms.onsite import OnSiteRapidCheckinForm, OnsiteBarcodeCheckinForm
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.accounting.controllers import IndividualAccountingController
from esp.utils.web import render_to_response
from django.contrib.auth.decorators import login_required
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
            "seq": 1
            }

    def updatePaid(self, paid=True):   
        """ Close off the student's invoice and, if paid is True, create a receipt showing
        that they have paid all of the money they owe for the program. """
        if not self.hasPaid():
            iac = IndividualAccountingController(self.program, self.student)
            iac.add_required_transfers()
            if paid:
                iac.submit_payment(iac.amount_due())

    def create_record(self, event):
        if event=="paid":
            self.updatePaid(True)

        recs, created = Record.objects.get_or_create(user=self.student,
                                                     event=event,
                                                     program=self.program)
        return created

    def delete_record(self, extension):
        if event=="paid":
            self.updatePaid(False)

        recs = Record.objects.get_or_create(user=self.student,
                                            event=event,
                                            program=self.program)
        recs.delete()
        return True

    def hasAttended(self):
        return Record.user_completed(self.student, "attended",self.program)

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
        return str(u[0].time.strftime("%H:%M %d/%m/%y"))

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
            form = OnSiteRapidCheckinForm(request.POST)
            if form.is_valid():
                student = ESPUser(form.cleaned_data['user'])
                #   Check that this is a student user who is not also teaching (e.g. an admin)
                if student.isStudent() and student not in self.program.teachers()['class_approved']:
                    recs = Record.objects.filter(user=student, event="attended", program=prog)
                    if not recs.exists():
                        rec, created = Record.objects.get_or_create(user=student, event="attended", program=prog)
                    context['message'] = '%s %s marked as attended.' % (student.first_name, student.last_name)
                    if request.is_ajax():
                        return self.ajax_status(request, tl, one, two, module, extra, prog, context)
                else:
                    context['message'] = '%s %s is not a student and has not been checked in' % (student.first_name, student.last_name)
                    if request.is_ajax():
                        return self.ajax_status(request, tl, one, two, module, extra, prog, context)
        else:
            form = OnSiteRapidCheckinForm()
        
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
                        result=ESPUser.objects.filter(id=code)
                    except ValueError:
                        results['not_found'].append(code)
                    if len(result) > 1:
                        raise ESPError("Something weird happened, there are two students with ID %s." % code, log=False)
                    elif len(result) == 0:
                        results['not_found'].append(code)
                    else:
                        student=result[0]
                        if student.isStudent():
                            existing = Record.user_completed(student, 'attended', prog)
                            if existing:
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
    def checkin(self, request, tl, one, two, module, extra, prog):
        user, found = search_for_user(request, self.program.students_union())
        if not found:
            return user
        
        self.student = user
            
        if request.method == 'POST':
            for key in ['attended','paid','liab','med']:
                if request.POST.has_key(key):
                    self.create_record(key)
                else:
                    self.delete_record(key)
                

            return self.goToCore(tl)

        return render_to_response(self.baseDir()+'checkin.html', request, {'module': self, 'program': prog})


    class Meta:
        proxy = True
        app_label = 'modules'
