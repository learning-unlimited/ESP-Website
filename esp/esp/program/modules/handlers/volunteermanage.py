
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
  Email: web-team@learningu.org
"""

from esp.program.models import VolunteerRequest
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules.forms.volunteer import VolunteerRequestForm, VolunteerImportForm
from esp.utils.web import render_to_response
from esp.cal.models import Event
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
        response = None

        if extra == 'csv':
            response = HttpResponse(content_type="text/csv")
            requests = self.program.getVolunteerRequests()
            write_csv = csv.writer(response)
            write_csv.writerow(("Activity","Time","Name","Phone Number","E-mail Address"))
            for request in requests:
                for offer in request.get_offers():
                    write_csv.writerow((request.timeslot.description, request.timeslot.pretty_time(), offer.name, offer.phone, offer.email))
            response['Content-Disposition'] = 'attachment; filename=volunteers.csv'
            return response

        elif extra == "request_import":
            (response, context) = self.volunteer_import(request, tl, one, two, module, extra, prog)
            if response:
                return response
            else:
                form = VolunteerRequestForm(program=prog)

        elif 'op' in request.GET:
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

        context['shift_form'] = form
        if 'import_request_form' not in context:
            context['import_request_form'] = VolunteerImportForm()
        context['requests'] = self.program.getVolunteerRequests()
        return render_to_response('program/modules/volunteermanage/main.html', request, context)

    def volunteer_import(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        import_mode = 'preview'
        if 'import_confirm' in request.POST and request.POST['import_confirm'] == 'yes':
            import_mode = 'save'

        import_form = VolunteerImportForm(request.POST)
        if not import_form.is_valid():
            context['import_request_form'] = import_form
        else:
            past_program = import_form.cleaned_data['program']
            start_date = import_form.cleaned_data['start_date']

            #   Figure out timeslot dates
            new_requests = []
            prev_timeslots = []
            prev_requests = past_program.getVolunteerRequests().order_by('timeslot__start')
            for prev_request in prev_requests:
                prev_timeslots.append(prev_request.timeslot)
            time_delta = start_date - prev_timeslots[0].start.date()
            for i,orig_timeslot in enumerate(prev_timeslots):
                new_timeslot = Event(
                    program = self.program,
                    event_type = orig_timeslot.event_type,
                    short_description = orig_timeslot.short_description,
                    description = orig_timeslot.description,
                    priority = orig_timeslot.priority,
                    start = orig_timeslot.start + time_delta,
                    end   = orig_timeslot.end + time_delta,
                )
                #   Save the new timeslot and request only if it doesn't duplicate an existing one
                if import_mode == 'save' and not Event.objects.filter(program=new_timeslot.program, start=new_timeslot.start, end=new_timeslot.end).exists():
                    new_timeslot.save()
                new_request = VolunteerRequest()
                new_request.program = self.program
                new_request.timeslot = new_timeslot
                new_request.num_volunteers = prev_requests[i].num_volunteers
                if import_mode == 'save' and not VolunteerRequest.objects.filter(program=new_timeslot.program, timeslot=new_timeslot).exists():
                    new_request.save()
                new_requests.append(new_request)

            #   Render a preview page showing the resources for the previous program if desired
            context['past_program'] = past_program
            context['start_date'] = start_date.strftime('%m/%d/%Y')
            context['new_requests'] = new_requests
            if import_mode == 'preview':
                context['prog'] = self.program
                response = render_to_response(self.baseDir()+'request_import.html', request, context)
            else:
                extra = 'timeslot'

        return (response, context)

    class Meta:
        proxy = True
        app_label = 'modules'
