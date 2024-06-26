from __future__ import absolute_import
import six
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
import datetime

from django import forms

from esp.program.modules.base import ProgramModuleObj, needs_student_in_grade, needs_student_in_grade, meets_deadline, CoreModule, main_call, aux_call, meets_cap
from esp.program.models  import ClassSubject, ClassSection, StudentRegistration
from esp.accounting.controllers import IndividualAccountingController
from esp.utils.web import render_to_response
from esp.users.models    import Record, RecordType, Permission
from esp.cal.models import Event
from esp.middleware   import ESPError
from esp.survey.views   import survey_view
from esp.tagdict.models  import Tag
from django.http import HttpResponseRedirect

from esp.program.modules.handlers.studentregcore import StudentRegCore
from esp.program.modules.handlers.studentclassregmodule import StudentClassRegModule

class StudentOnsite(ProgramModuleObj, CoreModule):
    doc = """Serves a mobile-friendly interface for common onsite functions for students."""

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Student Onsite",
            "admin_title": "Student Onsite Webapp",
            "module_type": "learn",
            "seq": 9999,
            "choosable": 1
            }

    @main_call
    @needs_student_in_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def studentonsite(self, request, tl, one, two, module, extra, prog):
        """ Display the landing page for the student onsite webapp """
        context = self.onsitecontext(request, tl, one, two, prog)
        user = request.user
        scrm = prog.getModule("StudentClassRegModule")
        context.update(StudentClassRegModule.prepare_static(user, prog, scrm = scrm))
        context['deadline_met'] = scrm.deadline_met()

        context['webapp_page'] = 'schedule'
        context['scrmi'] = prog.studentclassregmoduleinfo
        context['checked_in'] = prog.isCheckedIn(user)
        context['checkin_note'] = Tag.getProgramTag('student_onsite_checkin_note', program = prog)

        return render_to_response(self.baseDir()+'schedule.html', request, context)

    @aux_call
    @needs_student_in_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def onsitedetails(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        user = request.user
        context['webapp_page'] = 'schedule'
        if extra:
            secid = extra
            sections = ClassSection.objects.filter(id = secid)
            if len(sections) == 1:
                section = sections[0]
                if StudentRegistration.valid_objects().filter(section=section, user=user, relationship__name="Enrolled"):
                    context['checked_in'] = prog.isCheckedIn(user)
                    surveys = prog.getSurveys().filter(category = tl)
                    context['has_survey'] = surveys.count() > 0 and surveys[0].questions.filter(per_class = True).exists()
                    first_block = section.firstBlockEvent()
                    if first_block:
                        context['has_started'] =  first_block.start < datetime.datetime.now()
                    context['section'] = section
                    return render_to_response(self.baseDir()+'sectioninfo.html', request, context)
        return HttpResponseRedirect(prog.get_learn_url() + 'studentonsite')

    @aux_call
    @needs_student_in_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def onsitemap(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        context['webapp_page'] = 'map'
        context['center'] = Tag.getProgramTag('program_center', program = prog)
        context['zoom'] = Tag.getProgramTag('program_center_zoom', program = prog)
        context['API_key'] = Tag.getTag('google_cloud_api_key')

        return render_to_response(self.baseDir()+'map.html', request, context)

    @aux_call
    @needs_student_in_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def onsitecatalog(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        user = request.user
        context['webapp_page'] = 'catalog'
        user_grade = user.getGrade(self.program)
        if extra:
            try:
                ts = Event.objects.get(id=int(extra), program=prog)
            except:
                raise ESPError('Please use the links on the schedule page.', log=False)
            context['timeslot'] = ts
            classes = list(ClassSubject.objects.catalog(prog, ts))
            classes = [c for c in classes if c.grade_min <=user_grade and c.grade_max >= user_grade]
            context['checked_in'] = Record.objects.filter(program=prog, event__name='attended', user=user).exists()

        else:
            classes = list(ClassSubject.objects.catalog(prog))

        categories_sort = StudentClassRegModule.sort_categories(classes, prog)

        context['classes'] = classes
        context['categories'] = categories_sort
        context['prereg_url'] = prog.get_learn_url() + 'onsiteaddclass'

        return render_to_response(self.baseDir()+'catalog.html', request, context)

    @aux_call
    @needs_student_in_grade
    @meets_deadline('/Webapp')
    @meets_cap
    def onsitesurvey(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        context['webapp_page'] = 'survey'
        return survey_view(request, tl, one, two, template = self.baseDir()+'survey.html', context = context)

    @aux_call
    @needs_student_in_grade
    @meets_deadline('/Webapp')
    def onsiteaddclass(self, request, tl, one, two, module, extra, prog):
        if StudentClassRegModule.addclass_logic(request, tl, one, two, module, extra, prog, webapp=True):
            return HttpResponseRedirect(prog.get_learn_url() + 'studentonsite')

    @aux_call
    @needs_student_in_grade
    @meets_deadline('/Webapp')
    def onsiteclearslot(self, request, tl, one, two, module, extra, prog):
        result = StudentClassRegModule.clearslot_logic(request, tl, one, two, module, extra, prog)
        if isinstance(result, six.string_types):
            raise ESPError(result, log=False)
        else:
            return HttpResponseRedirect(prog.get_learn_url() + 'studentonsite')

    @aux_call
    @needs_student_in_grade
    def selfcheckin(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        mode = Tag.getProgramTag('student_self_checkin', program = prog)
        user = request.user

        # Redirect to their schedule if self checkin is not available
        if mode == "none":
            return HttpResponseRedirect(prog.get_learn_url() + 'studentonsite')

        # Show message if they are already checked in
        checked_in = prog.isCheckedIn(user)
        context['checked_in'] = checked_in

        if not checked_in:
            # Show which modules and/or records they haven't completed
            # This only includes the required and non-completed subset of modules/records
            # that would normally be shown on the /studentreg page
            context['mode'] = mode
            context['form'] = SelfCheckinForm(program = prog, user = user)

            modules = prog.getModules(user, 'learn')
            context['completedAll'] = True
            for module in modules:
                # If completed all required modules so far...
                if context['completedAll']:
                    if not module.isCompleted() and module.isRequired():
                        context['completedAll'] = False

            records = StudentRegCore.get_reg_records(user, prog, 'learn')

            context['modules'] = [x for x in modules if (x.isRequired() and not x.isCompleted())]
            context['records'] = [x for x in records if not x['isCompleted']]

            if Tag.getBooleanTag('student_self_checkin_paid', program = prog):
                iac = IndividualAccountingController(prog, user)
                context['owes_money'] = iac.amount_due() > 0
                if context['owes_money']:
                    if Permission.user_has_perm(user, 'Student/Payment', prog):
                        if prog.hasModule("CreditCardModule_Stripe"):
                            context['payment_url'] = "payonline"
                        elif prog.hasModule("CreditCardModule_Cybersource"):
                            context['payment_url'] = "cybersource"

            if request.method == 'POST':
                form = SelfCheckinForm(request.POST, program = prog, user = user)
                if form.is_valid():
                    # Check in the student
                    rt = RecordType.objects.get(name="attended")
                    rec = Record(user=user, program=prog, event=rt)
                    rec.save()
                    return HttpResponseRedirect(prog.get_learn_url() + 'studentonsite')
                else:
                    context['form'] = form

        return render_to_response(self.baseDir()+'selfcheckin.html', request, context)

    @staticmethod
    def onsitecontext(request, tl, one, two, prog):
        context = {}
        surveys = prog.getSurveys().filter(category = tl).select_related()
        if len(surveys) == 0:
            context['survey_status'] = 'none'
        context['user'] = request.user
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        context['map_tab'] = bool(Tag.getTag('google_cloud_api_key').strip())
        return context

    def isStep(self):
        return Tag.getBooleanTag('student_webapp_isstep', program=self.program)

    class Meta:
        proxy = True
        app_label = 'modules'

class SelfCheckinForm(forms.Form):
    code = forms.CharField(min_length = 6, max_length = 6, required = True)

    def __init__(self, *args, **kwargs):
        if 'program' in kwargs and 'user' in kwargs:
            program = kwargs.pop('program')
            user = kwargs.pop('user')
        else:
            raise KeyError('Need to supply program and user as named arguments to SelfCheckinForm')
        super(SelfCheckinForm, self).__init__(*args, **kwargs)
        mode = Tag.getProgramTag('student_self_checkin', program = program)
        self.hash = user.userHash(program)
        if mode != 'code':
            self.fields['code'].initial = self.hash
            self.fields['code'].widget = forms.HiddenInput()

    def clean_code(self):
        data = self.cleaned_data['code']
        if data != self.hash:
            raise forms.ValidationError("That code is invalid")
        return data
