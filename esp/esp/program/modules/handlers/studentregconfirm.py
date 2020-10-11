
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

from esp.program.modules.base import ProgramModuleObj, needs_student, main_call, aux_call
from esp.middleware.threadlocalrequest import get_current_request
from django.http import HttpResponseRedirect

class StudentRegConfirm(ProgramModuleObj):
    """ Basically, a dirty hack to add a link to registration confirmation into the list of stuffs to do during reg """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": 'Add "Confirm Registration" link',
            "link_title": "Confirm Registration",
            "module_type": "learn",
            "seq": 99999,
            "choosable": 1,
            }

    @main_call
    @needs_student
    def do_confirmreg(self, request, tl, one, two, module, extra, prog):
        return HttpResponseRedirect("confirmreg")

    def isCompleted(self):
        return self.program.isConfirmed(get_current_request().user)

    def hideNotRequired(self):
        return True

    class Meta:
        proxy = True
        app_label = 'modules'
