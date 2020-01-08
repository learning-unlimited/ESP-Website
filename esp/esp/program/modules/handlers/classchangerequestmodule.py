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

from datetime import datetime
from urllib import quote

from esp.middleware.threadlocalrequest import get_current_request
from esp.program.models import Program, StudentAppResponse, StudentRegistration, RegistrationType
from esp.program.models.class_ import ClassSubject
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.base import main_call, aux_call, needs_admin, needs_student, meets_grade
from esp.utils.web import render_to_response
from esp.users.models import ESPUser
from esp.utils.query_utils import nest_Q

from django import forms
from django.http import HttpResponseRedirect



class ClassChangeRequestModule(ProgramModuleObj):
    doc = """Let students enter a lottery to switch classes after the program has started."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Class Change Request",
            "link_title": "Class Change Request",
            "module_type": "learn",
            "required": False,
            "choosable": 1,
        }

    class Meta:
        proxy = True
        app_label = 'modules'

    def isCompleted(self):
        return StudentRegistration.valid_objects().filter(user=get_current_request().user,
                                                          relationship__name="Request").exists()

    @main_call
    @needs_student
    @meets_grade
    def classchangerequest(self, request, tl, one, two, module, extra, prog):
        timeslots = prog.getTimeSlots()
        sections = prog.sections().filter(status=10, meeting_times__isnull=False).distinct()

        enrollments = {}
        for timeslot in timeslots:
            try:
                enrollments[timeslot] = ClassSubject.objects.get(nest_Q(StudentRegistration.is_valid_qobject(), 'sections__studentregistration'), sections__studentregistration__relationship__name="Enrolled", sections__studentregistration__user=request.user, sections__meeting_times=timeslot, parent_program=prog)
            except ClassSubject.DoesNotExist:
                enrollments[timeslot] = None

        context = {}
        context['timeslots'] = timeslots
        context['enrollments'] = enrollments
        context['user'] = request.user
        if 'success' in request.GET:
            context['success'] = True
        else:
            context['success'] = False

        if request.user.isStudent():
            sections_by_slot = dict([(timeslot,[(section, 1 == StudentRegistration.valid_objects().filter(user=context['user'], section=section, relationship__name="Request").count()) for section in sections if section.get_meeting_times()[0] == timeslot and section.parent_class.grade_min <= request.user.getGrade(prog) <= section.parent_class.grade_max and section.parent_class not in enrollments.values() and ESPUser.getRankInClass(request.user, section.parent_class) in (5,10)]) for timeslot in timeslots])
        else:
            sections_by_slot = dict([(timeslot,[(section, False) for section in sections if section.get_meeting_times()[0] == timeslot]) for timeslot in timeslots])

        fields = {}
        for i, timeslot in enumerate(sections_by_slot.keys()):
            choices = [('0', "I'm happy with my current enrollment.")]
            initial = '0'
            for section in sections_by_slot[timeslot]:
                choices.append((section[0].emailcode(), section[0].emailcode()+": "+section[0].title()))
                if section[1]:
                    initial = section[0].emailcode()
            fields['timeslot_'+str(i+1)] = forms.ChoiceField(label="Timeslot "+str(i+1)+" ("+timeslot.pretty_time()+")", choices=choices, initial=initial)

        form = type('ClassChangeRequestForm', (forms.Form,), fields)
        context['form'] = form()
        if request.method == "POST":
            old_requests = StudentRegistration.valid_objects().filter(user=context['user'], section__parent_class__parent_program=prog, relationship__name="Request")
            for r in old_requests:
                r.expire()
            form = form(request.POST)
            if form.is_valid():
                for value in form.cleaned_data.values():
                    section = None
                    for s in sections:
                        if s.emailcode() == value:
                            section = s
                            break
                    if not section:
                        continue
                    r = StudentRegistration.valid_objects().get_or_create(user=context['user'], section=section, relationship=RegistrationType.objects.get_or_create(name="Request", category="student")[0])[0]
                    r.save()

                return HttpResponseRedirect(request.path.rstrip('/')+'/?success')
        else:
            return render_to_response(self.baseDir() + 'classchangerequest.html', request, context)
