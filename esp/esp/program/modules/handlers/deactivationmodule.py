
from __future__ import absolute_import
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules.handlers.listgenmodule import ListGenModule
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser, PersistentQueryFilter
from esp.users.controllers.usersearch import UserSearchController
from esp.users.views.usersearch import get_user_list, get_user_checklist
from esp.middleware import ESPError

import logging

class DeactivationModule(ProgramModuleObj):
    doc = """Mass deactivate sets of users"""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Deactivation Module",
            "link_title": "Mass Deactivate Users",
            "module_type": "manage",
            "seq": 502,
            "choosable": 1,
        }

    @aux_call
    @needs_admin
    def deactivatefinal(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST' or 'filterid' not in request.GET:
            raise ESPError()('Filter has not been properly set')
        elif request.POST.get('confirm', '') == '':
            raise ESPError()('You must confirm that you want to deactivate these users.')

        # get the filter to use and text message to send from the request; this is set in grouptextpanel form
        filterObj = PersistentQueryFilter.objects.get(id=request.GET['filterid'])
        users = filterObj.getList(ESPUser)

        if not users:
            raise ESPError()("Your query did not match any users")

        logger = logging.getLogger(__name__)
        logger.info("Mass deactivated users: %s", ", ".join([str(user.id) for user in users]))
        n_users = users.update(is_active = False)

        return render_to_response(self.baseDir()+'finished.html', request, {'n_users': n_users})

    @main_call
    @needs_admin
    def deactivate(self, request, tl, one, two, module, extra, prog):
        usc = UserSearchController()
        context = {}
        context['program'] = prog

        if request.method == "POST":
            selected = None
            if request.POST.get('submit_checklist') == 'true':
                filterObj, found = get_user_list(request, prog.getLists(True))
                if not found:
                    return filterObj
            else:
                data = ListGenModule.processPost(request)
                filterObj = usc.filter_from_postdata(prog, data)
                selected = usc.selected_list_from_postdata(data)

                if data['use_checklist'] == '1':
                    (response, unused) = get_user_checklist(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, '/manage/%s/deactivate' % prog.getUrlBase(), extra_context = {'module': "Mass Deactivation Portal"})
                    return response

            context['filterid'] = filterObj.id
            context['selected'] = selected
            context['num_users'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
            return render_to_response(self.baseDir()+'options.html', request, context)

        context.update(usc.prepare_context(prog, target_path='/manage/%s/deactivate' % prog.url))
        return render_to_response(self.baseDir()+'search.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
