
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
  Email: web-team@lists.learningu.org
"""
from esp.program.modules.base    import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules         import module_ext
from esp.program.models          import Program, ClassSubject, ClassSection, ClassCategories, ClassSizeRange
from esp.datatree.models         import *
from esp.web.util                import render_to_response
from django                      import forms
from django.http                 import HttpResponseRedirect, HttpResponse
from django.template.loader      import render_to_string
from esp.cal.models              import Event
from esp.users.models            import User, ESPUser, UserBit, UserAvailability
from esp.middleware              import ESPError
from esp.resources.models        import Resource, ResourceRequest, ResourceType, ResourceAssignment
from esp.datatree.models         import DataTree
from datetime                    import timedelta
from django.utils                import simplejson
from collections                 import defaultdict
from esp.cache                   import cache_function
from uuid                        import uuid4 as get_uuid

class CheckAvailabilityModule(ProgramModuleObj):
    doc = """ Displays when a teacher is available based on availability and classes.. """

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Check Availability",
            "module_type": "manage",
            "seq": 9
            }
    
    def prepare(self, context={}):
        if context is None: context = {}

        context['schedulingmodule'] = self 
        return context

    @main_call
    @needs_admin
    def check_availability(self, request, tl, one, two, module, extra, prog):
        """
        Check availability of the specified user.
        """
        
        if not request.GET.has_key('user'):
            context = {}
            return render_to_response(self.baseDir()+'searchform.html', request, (prog, tl), context)
        
        try:
            teacher = ESPUser.objects.get(username=request.GET['user'])
        except:
            raise ESPError(False), "That username does not appear to exist!"

        # Get the times that the teacher marked they were available
        resources = UserAvailability.objects.filter(user=teacher).filter(QTree(event__anchor__below = prog.anchor))
        
        # Now get times that teacher is teaching
        classes = [cls for cls in teacher.getTaughtClasses() if cls.parent_program.id == prog.id ]
        times = set()
        
        for cls in classes:
            cls_secs = ClassSection.objects.filter(parent_class=cls)
            
            for cls_sec in cls_secs:
                sec_times = Event.objects.filter(meeting_times=cls_sec)
                
                for time in sec_times:
                    times.add(time)
        
        # Check which are truly available and mark in tuple as True, otherwise as False (will appear red)
        available = []
        
        for resource in resources:
            if resource.event not in times:
                available.append((resource.event.start, resource.event.end, True))
            else:
                available.append((resource.event.start, resource.event.end, False))

        context = {'available': available, 'teacher_name': teacher.first_name + ' ' + teacher.last_name}
        return render_to_response(self.baseDir()+'check_availability.html', request, (prog, tl), context)
