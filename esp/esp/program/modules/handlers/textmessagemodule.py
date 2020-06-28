
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

from esp.program.modules.base import ProgramModuleObj, main_call, aux_call
from django.http import HttpResponseRedirect
from django import forms
from localflavor.us.forms import USPhoneNumberField
from esp.program.models import RegistrationProfile
from esp.middleware.threadlocalrequest import get_current_request
class TextMessageForm(forms.Form):
    phone_number = USPhoneNumberField()

class TextMessageModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": 'Text Message Reminders',
            "link_title": "Text Message Reminders",
            "module_type": "learn",
            "inline_template": "textmessage.html",
            "seq": 100,
            "choosable": 1
            }

    def prepare(self, context):
        context['textmessage_form'] = TextMessageForm()

        profile = RegistrationProfile.getLastForProgram(get_current_request().user, self.program)
        if profile.text_reminder is True:
            if profile.contact_user:
                context['textmessage_form'] = TextMessageForm(initial={'phone_number': profile.contact_user.phone_cell})

        return context

    def onConfirm(self, request):
        form = TextMessageForm(request.POST)
        student = request.user
        if form.is_valid() and len(form.cleaned_data['phone_number']) > 0:
            profile = RegistrationProfile.getLastForProgram(student, self.program)
            profile.text_reminder = True
            profile.save()
            profile.contact_user.phone_cell = form.cleaned_data['phone_number']
            profile.contact_user.save()
        else:
            profile = RegistrationProfile.getLastForProgram(student, self.program)
            profile.text_reminder = False
            profile.save()

    class Meta:
        proxy = True
        app_label = 'modules'
