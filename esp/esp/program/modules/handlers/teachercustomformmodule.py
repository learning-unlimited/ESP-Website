
from __future__ import absolute_import
from six.moves import range
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call

from esp.users.models import ESPUser, Record, RecordType
from esp.customforms.models import Form
from esp.customforms.DynamicForm import FormHandler, ComboForm
from esp.customforms.DynamicModel import DynamicModelHandler
from esp.tagdict.models import Tag

from esp.middleware import ESPError
from esp.middleware.threadlocalrequest import get_current_request

from django import forms
from django.db.models.query import Q

class TeacherCustomComboForm(ComboForm):
    template_name = "program/modules/customformmodule/custom_form.html"
    event = "teacher_extra_form_done"
    program = None

    def done(self, form_list, **kwargs):
        # Delete old records, if any exist, and then make a new one
        rt = RecordType.objects.get(name = self.event)
        Record.objects.filter(user=self.curr_request.user, program=self.program, event=rt).delete()
        Record.objects.create(user=self.curr_request.user, program=self.program, event=rt)
        return super(TeacherCustomComboForm, self).done(form_list=form_list, redirect_url = '/teach/'+self.program.getUrlBase()+'/teacherreg', **kwargs)

class TeacherCustomFormModule(ProgramModuleObj):
    doc = """Serve a custom form as part of teacher registration."""

    def __init__(self, *args, **kwargs):
        super(TeacherCustomFormModule, self).__init__(*args, **kwargs)
        self.event = "teacher_extra_form_done"

    @classmethod
    def module_properties(cls):
        return [ {
            "module_type": "teach",
            'required': False,
            'admin_title': 'Teacher Custom Form',
            'link_title': 'Additional Teacher Information',
            'seq': 4,
            'choosable': 0,
        } ]

    def teachers(self, QObject = False):
        """Returns lists of teachers who've completed the custom form."""

        qo = Q(record__event__name=self.event, record__program=self.program)
        if QObject is True:
            return {
                'teacher_custom_form': qo,
            }
        else:
            return {
                'teacher_custom_form': ESPUser.objects.filter(qo).distinct(),
            }

    def teacherDesc(self):
        return {
            'teacher_custom_form': """Teachers who have completed the custom form""",
        }

    def isCompleted(self):
        """Return true if user has filled out the teacher custom form."""
        if hasattr(self, 'user'):
            user = self.user
        else:
            user = get_current_request().user
        return Record.objects.filter(user=user, program=self.program, event__name=self.event).exists()

    @staticmethod
    def get_prev_data(form, request):
        dmh = DynamicModelHandler(form)
        form_model = dmh.createDynModel()
        prev_results = form_model.objects.filter(user=request.user).order_by('-id')
        prev_result_data = {}
        if prev_results.exists():
            form_wizard = FormHandler(form, request, request.user).get_wizard()
            for step in range(len(form_wizard.form_list)):
                field_dict = {}
                plain_form = form_wizard.get_form(step)
                #   Load previous results, with a hack for multiple choice questions.
                for field in plain_form.fields:
                    #   Some fields aren't saved or don't have values (e.g., instruction fields)
                    if not hasattr(prev_results[0], field):
                        continue
                    elif isinstance(plain_form.fields[field], forms.MultipleChoiceField):
                        field_dict[field] = getattr(prev_results[0], field).split(';')
                    else:
                        field_dict[field] = getattr(prev_results[0], field)
                prev_result_data[str(step)] = field_dict
        return prev_result_data

    @main_call
    @needs_teacher
    def extraform(self, request, tl, one, two, module, extra, prog):
        custom_form_id = Tag.getProgramTag('teach_extraform_id', prog)
        if custom_form_id:
            cf = Form.objects.get(id=int(custom_form_id))
        else:
            raise ESPError('Cannot find an appropriate form for this module.  Please ask your administrator to create a form and set the teach_extraform_id Tag.', log=False)

        #   If the user already filled out the form, use their earlier response for the initial values
        if self.isCompleted():
            prev_result_data = self.get_prev_data(cf, request)
            return FormHandler(cf, request, request.user).get_wizard_view(wizard_view=TeacherCustomComboForm, initial_data = prev_result_data,
                               extra_context = {'prog': prog, 'qsd_name': 'teach:customform_header', 'module': self.module.link_title}, program = prog)
        else:
            return FormHandler(cf, request, request.user).get_wizard_view(wizard_view=TeacherCustomComboForm,
                               extra_context = {'prog': prog, 'qsd_name': 'teach:customform_header', 'module': self.module.link_title}, program = prog)

    def isStep(self):
        custom_form_id = Tag.getProgramTag('teach_extraform_id', self.program)
        return custom_form_id and Form.objects.filter(id=int(custom_form_id)).exists()

    class Meta:
        proxy = True
        app_label = 'modules'
