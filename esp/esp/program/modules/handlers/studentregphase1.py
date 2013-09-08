
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
from esp.program.modules.base    import ProgramModuleObj, main_call, aux_call, meets_deadline, needs_student, meets_grade
from esp.web.util                import render_to_response
# from django                      import forms
# from django.http                 import HttpResponseRedirect, HttpResponse
# from django.template.loader      import render_to_string
# from esp.cal.models              import Event
from esp.users.models            import User, ESPUser, UserAvailability
# from esp.middleware              import ESPError
# from esp.resources.models        import Resource, ResourceRequest, ResourceType, ResourceAssignment
# from esp.datatree.models         import DataTree
# from datetime                    import datetime, timedelta
# from django.utils                import simplejson
# from collections                 import defaultdict
# from esp.cache                   import cache_function
# from uuid                        import uuid4 as get_uuid
from django.db.models.query      import Q
# from django.views.decorators.cache import cache_control
# from esp.middleware.threadlocalrequest import get_current_request
    
class StudentRegPhase1(ProgramModuleObj):

    def students(self, QObject = False):
        # TODO: fill this in
        q = Q()
        if QObject:
            return {'phase1_students': q}
        else:
            return {'phase1_students': ESPUser.objects.filter(q).distinct()}

    def studentDesc(self):
        return {'phase1_students': "Students who have completed student registration phase 1"}

    def isCompleted(self):
        # TODO: fill this in
        return True

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Student Registration Phase 1",
            "admin_title": "Student Registration Phase 1",
            "module_type": "learn",
            "seq": 5
            }
    
    @main_call
    @needs_student
    def studentreg_1(self, request, tl, one, two, module, extra, prog):
        return render_to_response(self.baseDir() + 'studentreg_1.html', request, {})
    
    class Meta:
        abstract = True
