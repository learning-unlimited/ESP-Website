
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.program.models import StudentRegistration, RegistrationType
from esp.users.models import ESPUser
from esp.utils.web import render_to_response

class UnenrollModule(ProgramModuleObj):
    """ Frontend to kick students from classes. """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Unenroll Students",
            "link_title": "Unenroll Students",
            "module_type": "manage",
            "seq": 10,
        }

    class Meta:
        proxy = True
        app_label = 'modules'

    @main_call
    @needs_admin
    def unenroll_students(self, request, tl, one, two, module, extra, prog):
        """
        A form for selecting which students to kick from which sections,
        based on the students' first class times and the sections' start
        times.

        """
        context = {}
        context['timeslots'] = prog.getTimeSlotList()
        return render_to_response(
            self.baseDir()+'select.html', request, context)
