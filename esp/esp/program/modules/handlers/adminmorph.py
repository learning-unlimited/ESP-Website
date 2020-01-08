
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
from django.http     import HttpResponseRedirect
from esp.users.views import search_for_user
from django.db.models.query   import Q
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules.handlers.programprintables import ProgramPrintables
from esp.utils.web import render_to_response
from esp.users.models import ESPUser

import operator

class AdminMorph(ProgramModuleObj):
    doc = """ User morphing allows the program director to morph into a constituent of their program. """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "User Morphing Capability",
            "link_title": "Morph into User",
            "module_type": "manage",
            "seq": 34,
            "choosable": 1,
            }

    @main_call
    @needs_admin
    def admin_morph(self, request, tl, one, two, module, extra, prog):
        """ This function will allow someone to morph into a user for testing purposes. """

        #   If there's no 'extra' component to the URL, return the options page.
        if extra is None or extra == '':
            context = {'module': self}
            return render_to_response(self.baseDir()+'options.html', request, context)

        #   Prepare Q objects for common student, teacher, and volunteer searches.
        #   This used to use Program.students_union() et al, but those are way too complicated queries.
        search_keys = {
            'student': ['profile', 'enrolled', 'lotteried_students', 'confirmed'],
            'teacher': ['profile', 'class_submitted'],
            'volunteer': ['volunteer_all'],
        }
        saved_queries = {}
        self.program.setup_user_filters()
        for key in search_keys:
            user_list = getattr(self.program, key + 's')(QObjects=True)
            saved_queries[key] = reduce(operator.or_, [user_list[user_type] for user_type in search_keys[key] if user_type in user_list], Q())
        saved_queries['program'] = reduce(operator.or_, saved_queries.values())
        saved_queries['all'] = Q()

        #   Default to using all program participants, if no query type is specified
        if extra in saved_queries:
            query = saved_queries[extra]
        else:
            query = saved_queries['program']

        user, found = search_for_user(request, ESPUser.objects.filter(query))

        if not found:
            return user

        request.user.switch_to_user(request,
                                 user,
                                 '/manage/%s/admin_morph/' % prog.getUrlBase(),
                                 'Managing %s' % self.program.niceName(),
                                 False)

        return HttpResponseRedirect('/')


    class Meta:
        proxy = True
        app_label = 'modules'
