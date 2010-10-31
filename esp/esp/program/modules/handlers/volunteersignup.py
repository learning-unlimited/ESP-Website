
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

from esp.program.modules.base import ProgramModuleObj, CoreModule
from esp.web.util        import render_to_response
from esp.program.modules.forms.volunteer import VolunteerOfferForm
from esp.users.models import ESPUser, AnonymousUser

class VolunteerSignup(ProgramModuleObj, CoreModule):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Volunteer Sign-up Module",
            "link_title": "Sign Up to Volunteer",
            "module_type": "volunteer",
            "seq": 0,
            "main_call": "signup",
            "aux_calls": "view",
            }

    def signup(self, request, tl, one, two, module, extra, prog):
        context = {}
        
        if request.method == 'POST':
            form = VolunteerOfferForm(request.POST, program=prog)
            if form.is_valid():
                offers = form.save()
                context['complete'] = True
                context['complete_name'] = offers[0].name
                context['complete_email'] = offers[0].email
                context['complete_phone'] = offers[0].phone
                form = VolunteerOfferForm(program=prog)
        else:
            form = VolunteerOfferForm(program=prog)
            
        #   Pre-fill information if possible
        if hasattr(self.user, 'email'):
            form.load(self.user)
        
        #   Override default appearance; template doesn't mind taking a string instead
        context['form'] = form._html_output(
            normal_row = u'<tr%(html_class_attr)s><th>%(label)s</th><td>%(errors)s%(field)s%(help_text)s</td></tr>',
            error_row = u'<tr><td colspan="2">%s</td></tr>',
            row_ender = u'</td></tr>',
            help_text_html = u'%s',
            errors_on_separate_row = False)
        
        return render_to_response('program/modules/volunteersignup/signup.html', request, (prog, tl), context)
