
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
from esp.users.models   import ESPUser, PersistentQueryFilter, Record, RecordType
from esp.users.controllers.usersearch import UserSearchController
from esp.users.views.usersearch import get_user_checklist, get_user_list
from esp.middleware import ESPError

class UserRecordsModule(ProgramModuleObj):
    doc = """Set arbitrary records for an arbitrary list of users"""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "User Records Module",
            "link_title": "Manage User Records",
            "module_type": "manage",
            "seq": 501,
            "choosable": 1,
        }

    @aux_call
    @needs_admin
    def userrecordsfinal(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST' or 'filterid' not in request.GET:
            raise ESPError()('User filter has not been properly set')

        filterObj = PersistentQueryFilter.objects.get(id=request.GET['filterid'])
        users = filterObj.getList(ESPUser)
        try:
            users = users.distinct()
        except:
            pass

        if not users:
            raise ESPError()("Your query did not match any users")

        records = request.POST.getlist('records')
        Record.objects.bulk_create([Record(event=RecordType.objects.get(name=rec), program = prog, user=user) for rec in records for user in users])

        context = {'num_users': users.count(), 'records': records}

        return render_to_response(self.baseDir()+'finished.html', request, context)

    @main_call
    @needs_admin
    def userrecords(self, request, tl, one, two, module, extra, prog):
        usc = UserSearchController()
        context = {}
        context['program'] = prog
        context['records'] = list(RecordType.desc())

        if request.method == "POST":
            selected = []
            data = ListGenModule.processPost(request)
            if data.get('submit_checklist') == 'true':
                filterObj, found = get_user_list(request, self.program.getLists(True))
                selected = usc.selected_list_from_postdata(data)
            else:
                filterObj = UserSearchController().filter_from_postdata(prog, data)

            if data.get('use_checklist') == '1':
                (response, unused) = get_user_checklist(request, ESPUser.objects.filter(filterObj.get_Q()).distinct(), filterObj.id, '/manage/%s/userrecords' % prog.getUrlBase(), extra_context = {'module': "User Records Portal"})
                return response

            context['selected'] = selected
            context['filterid'] = filterObj.id
            context['num_users'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
            return render_to_response(self.baseDir()+'options.html', request, context)

        context.update(usc.prepare_context(prog, target_path='/manage/%s/userrecords' % prog.url))
        return render_to_response(self.baseDir()+'search.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
