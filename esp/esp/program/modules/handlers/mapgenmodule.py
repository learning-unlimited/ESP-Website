
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
from esp.users.models   import ESPUser, ContactInfo
from esp.users.controllers.usersearch import UserSearchController
from django.conf import settings

import csv
import json
from collections import Counter

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
        """ Select a group of users and generate a map summarizing their geographic distribution. """
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

            users = ESPUser.objects.filter(filterObj.get_Q()).distinct()
            context['num_users'] = users.count()

            #   Summarize users by state and zip code
            #   Only get contact infos that are for the actual users (not guardians or emergency contacts)
            states_raw = ContactInfo.objects.filter(user__in=users, as_user__isnull=False
                ).distinct('user').values_list('address_state', flat = True)
            states = dict(Counter([x for x in states_raw if x]))

            zipcodes_raw = ContactInfo.objects.filter(user__in=users, as_user__isnull=False
                ).distinct('user').values_list('address_zip', flat = True)
            zipcodes = dict(Counter([x for x in zipcodes_raw if x]))

            #   If we don't have state data, use zip code data to populate it
            #   data is from https://data.world/niccolley/us-zipcode-to-county-state
            csvfile = open(settings.MEDIA_ROOT + 'data/zipcode-data-2018.csv', "r")
            reader = csv.DictReader(csvfile)
            zip_states = {}
            for line in reader:
                zip = line['ZIP'].zfill(5)
                state = line['STATE']
                if state not in zip_states:
                    zip_states[state] = 0
                zip_states[state] += zipcodes.get(zip, 0)
            csvfile.close()
            states_corr = {state: (states.get(state, 0) if states.get(state, 0) > zip_states[state] else zip_states[state]) for state in zip_states.keys()}

            #   Render a page with a map
            context['states'] = json.dumps(states_corr)
            context['zipcodes'] = json.dumps(zipcodes)
            return render_to_response(self.baseDir()+'map.html', request, context)

        #   Render a page that shows the list selection options
        context.update(usc.prepare_context(prog, target_path='/manage/%s/usermap' % prog.url))
        return render_to_response(self.baseDir()+'search.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
