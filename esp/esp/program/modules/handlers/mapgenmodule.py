
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser
from esp.users.controllers.usersearch import UserSearchController

class MapGenModule(ProgramModuleObj):
    """ Allows you to generate a map showing the distribution of the selected users. """
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "User Map Generator",
            "link_title": "Generate Map of Users",
            "module_type": "manage",
            "seq": 500,
            "choosable": 1,
            }

    @main_call
    @needs_admin
    def usermap(self, request, tl, one, two, module, extra, prog):
        """ Select a group of users and generate a list of information
            about them using the generateList view above. """
        usc = UserSearchController()

        context = {}
        context['program'] = prog

        if request.method == 'POST':
            #   Turn multi-valued QueryDict into standard dictionary
            data = {}
            for key in request.POST:
                #   Some keys have list values
                if key in ['regtypes']:
                    data[key] = request.POST.getlist(key)
                else:
                    data[key] = request.POST[key]
            filterObj = usc.filter_from_postdata(prog, data)

            context['num_users'] = ESPUser.objects.filter(filterObj.get_Q()).distinct().count()

            #   Summarize users by county
            return render_to_response(self.baseDir()+'map.html', request, context)

        #   Render a page that shows the list selection options
        context.update(usc.prepare_context(prog, target_path='/manage/%s/usermap' % prog.url))
        return render_to_response(self.baseDir()+'search.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
