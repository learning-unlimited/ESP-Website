
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
from esp.program.modules.base    import ProgramModuleObj, needs_admin, main_call
from esp.middleware              import ESPError
from esp.utils.web               import render_to_response
from esp.users.models            import ESPUser
from esp.users.forms.generic_search_form import TeacherSearchForm
from esp.program.modules.handlers.availabilitymodule import AvailabilityModule


class CheckAvailabilityModule(ProgramModuleObj):
    """ This program module allows admins to check a teacher's availability for the program. """

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Teacher Availability Checker",
            "link_title": "Check Teacher Availability",
            "module_type": "manage",
            "seq": 0,
            "choosable": 1,
            } ]

    @main_call
    @needs_admin
    def edit_availability(self, request, tl, one, two, module, extra, prog):
        """
        Admins edits availability of the specified user.
        """

        target_id = None

        if 'user' in request.GET:
            target_id = request.GET['user']
        elif 'user' in request.POST:
            target_id = request.POST['user']
        elif 'target_user' in request.POST:
            target_id = request.POST['target_user']
        else:
            form = TeacherSearchForm()
            context = {'search_form': form, 'isAdmin': True, 'prog': self.program}
            return render_to_response('program/modules/availabilitymodule/availability_form.html', request, context)

        try:
            teacher = ESPUser.objects.get(id=target_id)
        except:
            try:
                teacher = ESPUser.objects.get(username=target_id)
            except:
                raise ESPError("The user with id/username=" + str(target_id) + " does not appear to exist!", log=False)
        availability = AvailabilityModule(program = prog)
        return availability.availabilityForm(request, tl, one, two, prog, teacher, True)

    class Meta:
        proxy = True
        app_label = 'modules'
