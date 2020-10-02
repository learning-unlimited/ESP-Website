
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


from esp.program.modules.base import ProgramModuleObj, CoreModule, main_call, aux_call, no_auth, meets_deadline, needs_account
from esp.middleware import ESPError
from esp.cal.models import Event
from esp.utils.web import render_to_response
from esp.program.modules.forms.volunteer import VolunteerOfferForm
from esp.users.models import ESPUser
from esp.program.models import VolunteerOffer
from django.db.models.query import Q
from esp.tagdict.models import Tag

class VolunteerSignup(ProgramModuleObj, CoreModule):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Volunteer Sign-up Module",
            "link_title": "Sign Up to Volunteer",
            "module_type": "volunteer",
            "seq": 0,
            "choosable": 1,
            }

    def require_auth(self):
        return Tag.getBooleanTag('volunteer_require_auth', self.program)

    @main_call
    @no_auth
    @meets_deadline("/Signup")
    def signup(self, request, tl, one, two, module, extra, prog):
        return self.signupForm(request, tl, one, two, prog, request.user)

    @staticmethod
    def signupForm(request, tl, one, two, prog, volunteer, isAdmin=False):
        context = {}

        if request.method == 'POST':
            form = VolunteerOfferForm(request.POST, program=prog)
            if form.is_valid():
                offers = form.save()
                if len(offers) > 0:
                    context['complete'] = True
                    context['complete_name'] = offers[0].name
                    context['complete_email'] = offers[0].email
                    context['complete_phone'] = offers[0].phone
                else:
                    context['cancelled'] = True
                form = VolunteerOfferForm(program=prog)
        else:
            form = VolunteerOfferForm(program=prog)

        #   Pre-fill information if possible
        if hasattr(volunteer, 'email'):
            form.load(volunteer)

        context['form'] = form

        vrs = prog.getVolunteerRequests()
        time_options = [v.timeslot for v in vrs]
        time_options_dict = dict(zip(time_options, vrs))

        #   Group contiguous blocks
        if not Tag.getBooleanTag('availability_group_timeslots'):
            time_groups = [list(time_options)]
        else:
            time_groups = Event.group_contiguous(list(time_options))

        context['groups'] = [[{'slot': t, 'id': time_options_dict[t].id} for t in group] for group in time_groups]

        context['isAdmin'] = isAdmin

        return render_to_response('program/modules/volunteersignup/signup.html', request, context)

    def volunteers(self, QObject=False):
        requests = self.program.volunteerrequest_set.all()
        queries = {'volunteer_all': Q(volunteeroffer__request__program=self.program)}
        for req in requests:
            key = 'volunteer_%d' % req.id
            queries[key] = Q(volunteeroffer__request=req)

        result = {}
        for key in queries:
            if QObject:
                result[key] = queries[key]
            else:
                result[key] = ESPUser.objects.filter(queries[key]).distinct()
        return result

    def volunteerDesc(self):
        base_dict = {'volunteer_all': 'All onsite volunteers for %s' % self.program.niceName()}
        requests = self.program.volunteerrequest_set.all()
        for req in requests:
            key = 'volunteer_%d' % req.id
            base_dict[key] = 'Volunteers for shift "%s"' % req.timeslot.description
        return base_dict

    @aux_call
    @needs_account
    def volunteerschedule(self, request, tl, one, two, module, extra, prog):
        #   Use the template defined in ProgramPrintables
        from esp.program.modules.handlers import ProgramPrintables
        context = {'module': self}
        pmos = ProgramModuleObj.objects.filter(program=prog,module__handler__icontains='printables')
        if pmos.count() == 1:
            pmo = ProgramPrintables(pmos[0])
            if request.user.isAdmin() and 'user' in request.GET:
                volunteer = ESPUser.objects.get(id=request.GET['user'])
            else:
                volunteer = request.user
            scheditems = []
            offers = VolunteerOffer.objects.filter(user=volunteer, request__program=self.program)
            for offer in offers:
                scheditems.append({'name': volunteer.name(),
                                   'volunteer': volunteer,
                                   'offer' : offer})
            #sort the offers by timeslot
            scheditems.sort(key=lambda item: item['offer'].request.timeslot.start)
            context['scheditems'] = scheditems
            return render_to_response(pmo.baseDir()+'volunteerschedule.html', request, context)
        else:
            raise ESPError('No printables module resolved, so this document cannot be generated.  Consult the webmasters.', log=False)

    class Meta:
        proxy = True
        app_label = 'modules'
