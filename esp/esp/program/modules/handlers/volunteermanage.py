
from __future__ import absolute_import
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

import codecs
from esp.program.models import VolunteerRequest
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.modules.forms.volunteer import VolunteerRequestForm, VolunteerImportForm
from esp.program.modules.handlers.volunteersignup import VolunteerSignup
from esp.users.models import ESPUser
from esp.utils.web import render_to_response
from esp.cal.models import Event
from esp.middleware import ESPError
from django.http import HttpResponse, HttpResponseRedirect
import csv

class VolunteerManage(ProgramModuleObj):
    doc = """Manage timeslots for volunteers and the volunteers that have signed up for those timeslots."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Volunteer Management",
            "link_title": "Manage Volunteers",
            "module_type": "manage",
            "seq": 0,
            "choosable": 1,
            }

    """
        Create/delete timeslots for volunteers
        Set number of timeslots that each timeslot needs (create/edit VolunteerRequests)
        Import timeslots from previous programs
        See who has signed up for each timeslot
        Invite people to volunteer via comm panel
    """

    @main_call
    @needs_admin
    def volunteering(self, request, tl, one, two, module, extra, prog):
        context = {}

        volunteer_dict = self.program.volunteers()
        context['num_vol'] = volunteer_dict['volunteer_all'].count()

        if extra == 'csv':
            response = HttpResponse(content_type="text/csv")
            requests = self.program.getVolunteerRequests()
            write_csv = csv.writer(response)
            write_csv.writerow(("Activity", "Time", "Name", "Phone Number", "Email Address", "Comments"))
            for request in requests:
                for offer in request.get_offers():
                    write_csv.writerow([codecs.encode(entry, 'utf-8') if entry is not None else '' for entry in
                        (request.timeslot.description, request.timeslot.pretty_time(), offer.name, offer.phone, offer.email, offer.comments)])
            response['Content-Disposition'] = 'attachment; filename=volunteers.csv'
            return response

        elif 'import' in request.POST or 'import_confirm' in request.POST:
            (response, context) = self.volunteer_import(request, tl, one, two, module, extra, prog)
            if response: # Show the import confirmation page
                return response
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
            context['import_request_form'] = VolunteerImportForm(cur_prog = prog)
        context['requests'] = self.program.getVolunteerRequests()
        return render_to_response('program/modules/volunteermanage/main.html', request, context)

    def volunteer_import(self, request, tl, one, two, module, extra, prog):
        context = {}
        response = None

        import_mode = 'preview'
        to_import = []
        if 'import_confirm' in request.POST and request.POST['import_confirm'] == 'yes':
            import_mode = 'save'
            to_import = request.POST.getlist('to_import')

        import_form = VolunteerImportForm(request.POST, cur_prog = prog)
        if not import_form.is_valid():
            context['import_request_form'] = import_form
        else:
            past_program = import_form.cleaned_data['program']
            start_date = import_form.cleaned_data['start_date']
            if past_program == prog:
                context['import_error'] = "You can only import shifts from previous programs"
            else:
                #Figure out timeslot dates
                new_requests = []
                prev_timeslots = []
                prev_requests = past_program.getVolunteerRequests()
                for prev_request in prev_requests:
                    prev_timeslots.append(prev_request.timeslot)
                time_delta = start_date - prev_timeslots[0].start.date()
                for i, orig_timeslot in enumerate(prev_timeslots):
                    new_timeslot = Event(
                        program = self.program,
                        start = orig_timeslot.start + time_delta,
                        end   = orig_timeslot.end + time_delta,
                        event_type = orig_timeslot.event_type,
                        short_description = orig_timeslot.short_description,
                        description = orig_timeslot.description,
                        priority = orig_timeslot.priority
                    )
                    #   Save the new timeslot only if it doesn't duplicate an existing one
                    if import_mode == 'save' and str(prev_requests[i].id) in to_import:
                        if Event.objects.filter(program=new_timeslot.program, start=new_timeslot.start, end=new_timeslot.end, event_type=new_timeslot.event_type).exists():
                            new_timeslot = Event.objects.get(program=new_timeslot.program, start=new_timeslot.start, end=new_timeslot.end, event_type=new_timeslot.event_type)
                        else:
                            new_timeslot.save()
                    new_request = VolunteerRequest(
                        program = self.program,
                        timeslot = new_timeslot,
                        num_volunteers = prev_requests[i].num_volunteers
                    )
                    #   Save the new timeslot only if it doesn't duplicate an existing one
                    if import_mode == 'save' and not VolunteerRequest.objects.filter(program=new_request.program, timeslot=new_timeslot,
                                                                                     num_volunteers=new_request.num_volunteers).exists() and str(prev_requests[i].id) in to_import:
                        new_request.save()
                    else:
                        new_request.old_id = prev_requests[i].id
                    new_requests.append(new_request)
                #   Render a preview page showing the resources for the previous program if desired
                context['past_program'] = past_program
                context['start_date'] = start_date.strftime('%m/%d/%Y')
                context['new_requests'] = new_requests
                if import_mode == 'preview':
                    context['prog'] = self.program
                    response = render_to_response(self.baseDir()+'import.html', request, context)

        return (response, context)

    @aux_call
    @needs_admin
    def check_volunteer(self, request, tl, one, two, module, extra, prog):
        """
        View and edit volunteer signups of the specified user.
        """
        target_id = None

        if 'user' in request.GET:
            target_id = request.GET['user']
        elif 'user' in request.POST:
            target_id = request.POST['user']
        else:
            context = {}
            return HttpResponseRedirect( '/manage/%s/%s/volunteering' % (one, two) )

        try:
            volunteer = ESPUser.objects.get(id=target_id)
        except:
            try:
                volunteer = ESPUser.objects.get(username=target_id)
            except:
                raise ESPError("The user with id/username=" + str(target_id) + " does not appear to exist!", log=False)

        vs = VolunteerSignup
        return vs.signupForm(request, tl, one, two, prog, volunteer, isAdmin=True)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
