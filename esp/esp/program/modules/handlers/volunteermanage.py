
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 by the individual contributors
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

from esp.program.models import VolunteerRequest
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules.forms.volunteer import VolunteerRequestForm
from esp.web.util        import render_to_response
from django.http import HttpResponse
import csv

class VolunteerManage(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Volunteer Management",
            "link_title": "Manage Volunteers",
            "module_type": "manage",
            "seq": 0,
            }

    """
        Create/delete timeslots for volunteers
        Set number of timeslots that each timeslot needs (create/edit VolunteerRequests)
        See who has signed up for each timeslot
        Invite people to volunteer via comm panel
    """
    
    @main_call
    @needs_admin
    def volunteering(self, request, tl, one, two, module, extra, prog):
        context = {}
        
        if extra == 'csv':
            response = HttpResponse(mimetype="text/csv")
            requests = self.program.getVolunteerRequests()
            write_csv = csv.writer(response)
            write_csv.writerow(("Activity","Time","Name","Phone Number","E-mail Address"))
            for request in requests:
                for offer in request.get_offers():
                    write_csv.writerow((request.timeslot.description, request.timeslot.pretty_time(), offer.name, offer.phone, offer.email))
            response['Content-Disposition'] = 'attachment; filename=volunteers.csv'
            return response
        
        if 'op' in request.GET:
            if request.GET['op'] == 'edit':
                form = VolunteerRequestForm(program=prog)
                form.load(VolunteerRequest.objects.get(id=request.GET['id']))
            elif request.GET['op'] == 'delete':
                form = VolunteerRequestForm(program=prog)
                VolunteerRequest.objects.get(id=request.GET['id']).delete()
        elif request.method == 'POST':
            form = VolunteerRequestForm(request.POST, program=prog)
            if form.is_valid():
                if form.cleaned_data['vr_id']:
                    form.save(VolunteerRequest.objects.get(id=form.cleaned_data['vr_id']))
                else:
                    form.save()
                form = VolunteerRequestForm(program=prog)
        else:
            form = VolunteerRequestForm(program=prog)
        
        context['form'] = form
        context['requests'] = self.program.getVolunteerRequests()
        return render_to_response('program/modules/volunteermanage/main.html', request, context)

    class Meta:
        abstract = True

