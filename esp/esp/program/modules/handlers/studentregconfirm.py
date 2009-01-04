
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

from esp.program.modules.base import ProgramModuleObj, CoreModule, main_call, aux_call
from django.http import HttpResponseRedirect

class StudentRegConfirm(ProgramModuleObj, CoreModule):
    """ Basically, a dirty hack to add a link to registration confirmation into the list of stuffs to do during reg """
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Confirm Registration",
            "module_type": "learn",
            "seq": 99999
            }
    
    @main_call
    def do_confirmreg(self, request, tl, one, two, module, extra, prog):
        return HttpResponseRedirect("confirmreg")

    def isCompleted(self):
        return self.program.isConfirmed(self.user)

    def hideNotRequired(self):
        return True
