
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
from esp.program.modules.base    import ProgramModuleObj, needs_admin, main_call, aux_call, meets_deadline, needs_student
from esp.program.modules         import module_ext
from esp.program.models          import Program, ClassSubject, ClassSection, ClassCategories, StudentRegistration
from esp.program.views           import lottery_student_reg, lsr_submit as lsr_view_submit
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
from datetime                    import datetime, timedelta
from django.utils                import simplejson
from collections                 import defaultdict
from esp.cache                   import cache_function
from uuid                        import uuid4 as get_uuid
from django.db.models.query      import Q
from django.views.decorators.cache import cache_control

class LotteryStudentRegModule(ProgramModuleObj):

    def students(self, QObject = False):
        q = Q(studentregistration__section__parent_class__parent_program=self.program, studentregistration__end_date__gte=datetime.now())
        if QObject:
            return {'lotteried_students': q}
        else:
            return {'lotteried_students': ESPUser.objects.filter(q).distinct()}

    def studentDesc(self):
        return {'lotteried_students': "Students who have entered the lottery"}

    def isCompleted(self):
        return bool(StudentRegistration.valid_objects().filter(section__parent_class__parent_program=self.program, user=self.user))

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Class Registration Lottery",
            "admin_title": "Lottery Student Registration",
            "module_type": "learn",
            "seq": 7
            }
    
        """ def prepare(self, context={}):
        if context is None: context = {}

        context['schedulingmodule'] = self 
        return context """

    @main_call
    @needs_student
    @meets_deadline('/Classes/Lottery')
    def lotterystudentreg(self, request, tl, one, two, module, extra, prog):
        """
        Serve the student reg page.

        This is just a static page;
        it gets all of its content from AJAX callbacks.
        """

        #print "blooble"
        #print request.user.username
        return render_to_response('program/modules/lotterystudentregmodule/student_reg.html', {'prog': self.program})

    @aux_call
    @meets_deadline('/Classes/Lottery')
    def lsr_submit(self, request, tl, one, two, module, extra, prog):
        """
        Currently a placeholder; someday this will get looped in
        to the actual lottery student reg so that it gets called.
        """

        return lsr_view_submit(request, self.program)


    @aux_call
    @needs_student
    @meets_deadline('/Classes/Lottery/View')
    def viewlotteryprefs(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['student'] = request.user
        context['program'] = prog

        priority_classids = set()
        uniquified_flags = []
        priority_flags = StudentRegistration.valid_objects().filter(user=request.user, section__parent_class__parent_program=prog, relationship__name='Priority/1')
        for flag in priority_flags:
            if flag.section.id not in priority_classids:
                priority_classids.add(flag.section.id)
                uniquified_flags.append(flag)
        context['priority'] = uniquified_flags
        if priority_flags.count() == 0:
            context['pempty'] = True
        else: context['pempty'] = False

        interested_classids = set()
        uniquified_interested = []
        interested = StudentRegistration.valid_objects().filter(user=request.user, section__parent_class__parent_program=prog, relationship__name='Interested')
        for flag in interested:
            if flag.section.id not in interested_classids:
                interested_classids.add(flag.section.id)
                uniquified_interested.append(flag)
        context['interested' ] = uniquified_interested
        if interested.count() == 0:
            context['iempty'] = True
        else: context['iempty'] = False

        return render_to_response(self.baseDir()+'view_lottery_prefs.html', request, (prog, tl), context)
