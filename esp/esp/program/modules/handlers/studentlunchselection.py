
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from esp.program.modules.base    import ProgramModuleObj, main_call, needs_student_in_grade, meets_cap, meets_deadline
from esp.program.models          import ClassSection, StudentRegistration, blocking_requirements
from esp.users.models            import Record, RecordType
from esp.middleware.threadlocalrequest import get_current_request
from esp.utils.web               import render_to_response

from django                      import forms

class StudentLunchSelectionForm(forms.Form):

    timeslot = forms.ChoiceField(choices=[], widget=forms.RadioSelect, label="Select a timeslot for your lunch period:")

    def __init__(self, program, user, day, *args, **kwargs):
        self.program = program
        self.user = user
        self.day = day

        super().__init__(*args, **kwargs)

        #   Set choices for timeslot field
        #   [(None, '')] +
        events_all = self.program.lunch_timeslots()
        events_filtered = [x for x in events_all if x.start.day == self.day.day]
        self.fields['timeslot'].choices = [(ts.id, ts.short_description) for ts in events_filtered] + [(-1, 'No lunch period')]

    def load_data(self):
        lunch_registrations = StudentRegistration.valid_objects().filter(user=self.user, section__parent_class__category__is_lunch=True, section__parent_class__parent_program=self.program).select_related('section').prefetch_related('section__meeting_times')
        lunch_registrations = [lunch_registration for lunch_registration in lunch_registrations if list(lunch_registration.section.meeting_times.all())[0].start.day == self.day.day]
        if len(lunch_registrations) > 0:
            section = lunch_registrations[0].section
            if len(section.get_meeting_times()) > 0:
                self.initial['timeslot'] = section.get_meeting_times()[0].id

    def save_data(self):
        #   The existing lunch periods for this day, which this choice replaces
        old_sections = [section for section in self.user.getSections(self.program)
                        if section.parent_class.category.is_lunch
                        and section.get_meeting_times()[0].start.day == self.day.day]

        new_sections = []
        if int(self.cleaned_data['timeslot']) != -1:
            new_sections = list(ClassSection.objects.filter(parent_class__parent_program=self.program, parent_class__category__is_lunch=True, meeting_times=self.cleaned_data['timeslot']))
            if len(new_sections) == 0:
                return (False, 'No lunch sections are available for that timeslot.')

        #   Declining lunch, or moving it, can violate an enforced constraint.
        #   Check the whole swap before giving up the existing registration.
        request = get_current_request()
        if not getattr(getattr(request, 'user', None), 'onsite_local', False):
            blocked = blocking_requirements(self.user, self.program,
                                            add_sections=new_sections[:1],
                                            remove_sections=old_sections)
            if blocked:
                return (False, 'You need to %s.' % blocked[0])

        for section in old_sections:
            section.unpreregister_student(self.user)

        if len(new_sections) == 0:
            return (True, 'Lunch period declined.')

        ca_msg = new_sections[0].cannotAdd(self.user)
        result = False if ca_msg else new_sections[0].preregister_student(self.user)
        if result:
            return (True, 'Registered for %s.' % new_sections[0])
        return (False, 'Failed to register for %s.  Please try another lunch period or remove conflicting classes from your schedule.' % new_sections[0])

class StudentLunchSelection(ProgramModuleObj):
    doc = """Allows students to enroll in lunch blocks."""
    permission_types = ('Student/Classes/Lunch',)

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Select Lunch Period",
            "admin_title": "Student Lunch Period Selection",
            "module_type": "learn",
            "required": True,
            "seq": 5,
            "choosable": 0,
            }

    def isCompleted(self, user=None):
        user = self._resolve_user(user)
        return Record.objects.filter(user=user, event__name="lunch_selected", program=self.program).exists()

    @main_call
    @needs_student_in_grade
    @meets_deadline('/Classes/Lunch')
    @meets_cap
    def select_lunch(self, request, tl, one, two, module, extra, prog):
        context = {'prog': self.program}
        user = request.user
        dates = prog.dates()

        if request.method == 'POST':
            forms = [StudentLunchSelectionForm(prog, user, dates[i], request.POST, prefix='day%d' % i) for i in range(len(dates))]
            all_valid = True
            success = True
            for form in forms:
                if not form.is_valid():
                    all_valid = False
            if all_valid:
                context['messages'] = []
                for form in forms:
                    (result, msg) = form.save_data()
                    if not result:
                        success = False
                    context['messages'] += [msg]
                if success:
                    rt = RecordType.objects.get(name="lunch_selected")
                    rec, created = Record.objects.get_or_create(user=user, program=prog, event=rt)
                    return self.goToCore(tl)
            else:
                context['errors'] = True
        else:
            forms = [StudentLunchSelectionForm(prog, user, dates[i], prefix='day%d' % i) for i in range(len(dates))]
            for i in range(len(forms)):
                forms[i].load_data()

        context['forms'] = forms

        return render_to_response(self.baseDir()+'select_lunch.html', request, context)

    def isStep(self):
        return self.program.lunch_timeslots().exists()

    class Meta:
        proxy = True
        app_label = 'modules'
