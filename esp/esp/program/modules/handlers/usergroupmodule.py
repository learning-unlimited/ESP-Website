
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
from esp.middleware import ESPError

from django.contrib.auth.models import Group

class UserGroupModule(ProgramModuleObj):
    doc = """Modify which users are in which user groups"""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "User Group Module",
            "link_title": "Manage User Groups",
            "module_type": "manage",
            "seq": 501,
            "choosable": 1,
        }

    @aux_call
    @needs_admin
    def usergroupfinal(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST' or 'filterid' not in request.GET or (request.POST.get('group_name_new', '') and request.POST.get('group_name_old', '')):
            raise ESPError()('Filter and/or group has not been properly set')

        # get the filter to use and text message to send from the request; this is set in grouptextpanel form
        filterObj = PersistentQueryFilter.objects.get(id=request.GET['filterid'])
        if request.POST.get('group_name_new', ''):
            group = request.POST['group_name_new']
        else:
            group = request.POST['group_name_old']
        clean = False
        if 'group_clean' in request.POST:
            clean = request.POST['group_clean']

        log = self.updateGroup(filterObj, group, clean)

        return render_to_response(self.baseDir()+'finished.html', request, {'log': log})

    @main_call
    @needs_admin
    def usergroup(self, request, tl, one, two, module, extra, prog):
        usc = UserSearchController()
        context = {}
        context['program'] = prog

        if request.method == "POST":
            data = ListGenModule.processPost(request)
            filterObj = UserSearchController().filter_from_postdata(prog, data)

            context['filterid'] = filterObj.id
            context['num_users'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()
            context['groups'] = Group.objects.all().values_list('name', flat=True)
            return render_to_response(self.baseDir()+'options.html', request, context)

        context.update(usc.prepare_context(prog, target_path='/manage/%s/usergroup' % prog.url))
        return render_to_response(self.baseDir()+'search.html', request, context)

    @staticmethod
    def updateGroup(filterobj, group_name, clean = False):
        """ Adds the specified users to the specified group. Removes anyone else if clean == True.
            Returns a log which can be displayed to user. """

        users = filterobj.getList(ESPUser)
        try:
            users = users.distinct()
        except:
            pass

        if not users:
            raise ESPError()("Your query did not match any users")

        group, created = Group.objects.get_or_create(name = group_name)

        diff1 = users.difference(group.user_set.all()).count()
        diff2 = group.user_set.all().difference(users).count()

        if clean:
            group.user_set.clear()

        group.user_set.add(*users)

        message = ""
        if created:
            message += "User group '%s' has been created. " % (group.name)
        if not created and clean:
            message += "%i users were removed from user group '%s'. " % (diff2, group.name)

        message += "%i new users have been added to user group '%s'. User group '%s' now has %i users." % (diff1, group.name, group.name, group.user_set.count())

        return message

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
