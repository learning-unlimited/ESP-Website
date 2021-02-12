
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call

from esp.utils.web import render_to_response

from esp.users.models import ESPUser, User, Record
from esp.customforms.models import Form
from esp.customforms.DynamicForm import FormHandler, ComboForm
from esp.customforms.DynamicModel import DynamicModelHandler
from esp.tagdict.models import Tag

from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request

from django import forms

import re

class CustomFormModule(ProgramModuleObj):

    def __init__(self, *args, **kwargs):
        super(CustomFormModule, self).__init__(*args, **kwargs)
        self.event = "extra_form_done"

    @classmethod
    def module_properties(cls):
        return [ {
            "module_type": "teach",
            'required': False,
            'admin_title': 'Teacher Custom Form',
            'link_title': 'Additional Profile Information',
            'seq': 4,
            'choosable': 0,
        },
        {
            "module_type": "learn",
            'required': False,
            'admin_title': 'Student Custom Form',
            'link_title': 'Additional Profile Information',
            'seq': 4,
            'choosable': 0,
        },]

    def isCompleted(self):
        """Return true if user has filled out the teacher quiz."""
        return Record.objects.filter(user=get_current_request().user, program=self.program, event=self.event).exists()

    @main_call
    @usercheck_usetl
    def extraform(self, request, tl, one, two, module, extra, prog):
        custom_form_id = Tag.getProgramTag('%s_extraform_id' % tl, prog)
        if custom_form_id:
            cf = Form.objects.get(id=int(custom_form_id))
        else:
            raise ESPError('Cannot find an appropriate form for the quiz.  Please ask your administrator to create a form and set the %s_extraform_id Tag.' % tl, log=False)

        form_wizard = FormHandler(cf, request, request.user).get_wizard()
        form_wizard.curr_request = request

        if request.method == 'POST':
            form = form_wizard.get_form(0, request.POST, request.FILES)
            if form.is_valid():
                #   Delete previous responses from this user
                dmh = DynamicModelHandler(cf)
                form_model = dmh.createDynModel()
                form_model.objects.filter(user=request.user).delete()
                form_wizard.done([form])
                bit, created = Record.objects.get_or_create(user=request.user, program=self.program, event=self.event)
                return self.goToCore(tl)
        else:
            #   If the user already filled out the form, use their earlier response for the initial values
            if self.isCompleted():
                dmh = DynamicModelHandler(cf)
                form_model = dmh.createDynModel()
                prev_results = form_model.objects.filter(user=request.user).order_by('-id')
                if prev_results.exists():
                    prev_result_data = {}
                    plain_form = form_wizard.get_form(0)
                    #   Load previous results, with a hack for multiple choice questions.
                    for field in plain_form.fields:
                        if isinstance(plain_form.fields[field], forms.MultipleChoiceField):
                            prev_result_data[field] = getattr(prev_results[0], field).split(';')
                        else:
                            prev_result_data[field] = getattr(prev_results[0], field)
                    form_wizard = FormHandler(cf, request, request.user).get_wizard(initial_data={0: prev_result_data})

            form = form_wizard.get_form(0)

        return render_to_response(self.baseDir()+'custom_form.html', request, {'prog':prog, 'form': form, 'qsd_name': tl+':customform_header'})

    class Meta:
        proxy = True
        app_label = 'modules'
