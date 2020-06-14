
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

from uuid                        import uuid4 as get_uuid
from datetime                    import datetime, timedelta
from collections                 import defaultdict
import json

from django                      import forms
from django.http                 import HttpResponseRedirect, HttpResponse
from django.template.loader      import render_to_string
from django.db.models.query      import Q
from django.views.decorators.cache import cache_control

from esp.program.modules.base    import ProgramModuleObj, needs_admin, main_call, aux_call, meets_deadline, needs_student, meets_grade, meets_cap, no_auth
from esp.program.modules         import module_ext
from esp.program.models          import Program, ClassSubject, ClassSection, ClassCategories, StudentRegistration
from esp.program.views           import lottery_student_reg, lsr_submit as lsr_view_submit
from esp.utils.web               import render_to_response
from esp.cal.models              import Event
from esp.users.models            import User, ESPUser, UserAvailability
from esp.middleware              import ESPError
from esp.resources.models        import Resource, ResourceRequest, ResourceType, ResourceAssignment
from argcache                    import cache_function
from esp.middleware.threadlocalrequest import get_current_request
from esp.utils.query_utils import nest_Q


class LotteryStudentRegModule(ProgramModuleObj):

    def students(self, QObject = False):
        q = Q(studentregistration__section__parent_class__parent_program=self.program) & nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration')
        if QObject:
            return {'lotteried_students': q}
        else:
            return {'lotteried_students': ESPUser.objects.filter(q).distinct()}

    def studentDesc(self):
        return {'lotteried_students': "Students who have entered the lottery"}

    def isCompleted(self):
        return bool(StudentRegistration.valid_objects().filter(section__parent_class__parent_program=self.program, user=get_current_request().user))

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Class Registration Lottery",
            "admin_title": "Lottery Student Registration",
            "module_type": "learn",
            "seq": 7,
            "choosable": 2,
            }

        """ def prepare(self, context={}):
        if context is None: context = {}

        context['schedulingmodule'] = self
        return context """

    @main_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    @meets_cap
    def lotterystudentreg(self, request, tl, one, two, module, extra, prog):
        """
        Serve the student reg page.

        This is just a static page;
        it gets all of its content from AJAX callbacks.
        """
        from django.conf import settings
        import json
        from django.utils.safestring import mark_safe

        crmi = prog.classregmoduleinfo

        open_class_category = prog.open_class_category
        # Convert the open_class_category ClassCategory object into a dictionary, only including the attributes the lottery needs or might need
        open_class_category = dict( [ (k, getattr( open_class_category, k )) for k in ['id','symbol','category'] ] )
        # Convert this into a JSON string, and mark it safe so that the Django template system doesn't try escaping it
        open_class_category = mark_safe(json.dumps(open_class_category))

        context = {'prog': prog, 'support': settings.DEFAULT_EMAIL_ADDRESSES['support'], 'open_class_registration': {False: 0, True: 1}[crmi.open_class_registration], 'open_class_category': open_class_category}

        ProgInfo = prog.studentclassregmoduleinfo

        #HSSP-style lottery
        if ProgInfo.use_priority == True and ProgInfo.priority_limit > 1:
            return render_to_response('program/modules/lotterystudentregmodule/student_reg_hssp.html', request, context)
        #Splark/Spash style lottery
        return render_to_response('program/modules/lotterystudentregmodule/student_reg_splash.html', request, context)

    @aux_call
    @needs_student
    @meets_deadline('/Classes/Lottery')
    def lsr_submit(self, request, tl, one, two, module, extra, prog):
        """
        Currently a placeholder; someday this will get looped in
        to the actual lottery student reg so that it gets called.
        """

        return lsr_view_submit(request, self.program)

    @aux_call
    @no_auth
    @cache_control(public=True, max_age=3600)
    def timeslots_json(self, request, tl, one, two, module, extra, prog, timeslot=None):
        """ Return the program timeslot names for the tabs in the lottery inteface """
        # using .extra() to select all the category text simultaneously
        ordered_timeslots = sorted(self.program.getTimeSlotList(), key=lambda event: event.start)
        ordered_timeslot_names = list()
        for item in ordered_timeslots:
            ordered_timeslot_names.append([item.id, item.short_description])

        resp = HttpResponse(content_type='application/json')

        json.dump(ordered_timeslot_names, resp)

        return resp


    @aux_call
    @needs_student
    @meets_deadline('/Classes/Lottery/View')
    def viewlotteryprefs(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['student'] = request.user

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

        return render_to_response(self.baseDir()+'view_lottery_prefs.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
