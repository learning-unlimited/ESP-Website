
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

from esp.program.modules.base import ProgramModuleObj, main_call, aux_call
from django.http import HttpResponseRedirect
from django import forms
from esp.users.forms.user_profile import PhoneNumberField
from esp.program.models import RegistrationProfile

class TextMessageForm(forms.Form):
    phone_number = PhoneNumberField(local_areacode='650')

class TextMessageModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": 'Text Message Reminders',
            "link_title": "Text Message Reminders",
            "module_type": "learn",
            "seq": 100
            }

    def prepare(self, context):
        context['textmessage_form'] = TextMessageForm()
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
            
