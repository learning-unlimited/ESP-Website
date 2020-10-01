
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

from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call
from esp.program.models import ClassSection
from esp.utils.web import render_to_response
from esp.users.forms.generic_search_form import StudentSearchForm
from esp.users.models    import ESPUser, Record
from esp.program.modules.handlers.studentclassregmodule import StudentClassRegModule
from esp.middleware.esperrormiddleware import ESPError

class OnSiteCheckoutModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "On-Site User Check-Out",
            "link_title": "Check-out Students",
            "module_type": "onsite",
            "seq": 1,
            "choosable": 1
            }

    @main_call
    @needs_onsite
    def checkout(self, request, tl, one, two, module, extra, prog):
        context = {}

        if "checkoutall" in request.POST and "confirm" in request.POST:
            students = prog.currentlyCheckedInStudents()
            for student in students:
                Record.objects.create(user=student, event="checked_out", program=prog)
            context['checkout_all_message'] = "Successfully checked out %s students" % (students.count())

        target_id = None
        student = None
        if 'target_user' in request.POST:
            form = StudentSearchForm(request.POST)
            if form.is_valid():
                student = form.cleaned_data['target_user']
        else:
            if 'user' in request.GET:
                target_id = request.GET['user']
            elif 'user' in request.POST:
                target_id = request.POST['user']
            if target_id:
                try:
                    student = ESPUser.objects.get(id=target_id)
                except:
                    try:
                        student = ESPUser.objects.get(username=target_id)
                    except:
                        raise ESPError("The user with id/username=" + str(target_id) + " does not appear to exist!", log=False)

        if student:
            context['student'] = student
            form = StudentSearchForm(initial={'target_user': student.id})

            # Get most recent check-in record
            if not prog.isCheckedIn(student):
                context['checkout_message'] = "Caution: %s (%s) is not currently checked in for this program!" % (student.name(), student.username)

            if 'checkout_student' in request.POST:
                # Make checked_out record
                Record.objects.create(user=student, event="checked_out", program=prog)

                # Unenroll student from selected classes
                for sec in ClassSection.objects.filter(id__in=filter(None, request.POST.getlist('unenroll'))).distinct():
                    sec.unpreregister_student(student, prereg_verb = "Enrolled")
                context['checkout_message'] = "Successfully checked out %s (%s)" % (student.name(), student.username)

            context.update(StudentClassRegModule.prepare_static(student, prog))
        else:
            form = StudentSearchForm()

        context['form'] = form
        return render_to_response(self.baseDir()+'checkout.html', request, context)


    class Meta:
        proxy = True
        app_label = 'modules'
