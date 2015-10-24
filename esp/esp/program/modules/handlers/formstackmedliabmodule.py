
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call, meets_cap
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, Permission, Record, User
from esp.tagdict.models import Tag
from django.db.models.query       import Q
from django.shortcuts import redirect
from esp.middleware.threadlocalrequest import get_current_request
from esp.users.forms.generic_search_form import GenericSearchForm

# hackish solution for Splash 2012
class FormstackMedliabModule(ProgramModuleObj):
    """ Module for collecting medical information online via Formstack """

    @classmethod
    def module_properties(cls):
        return [{
                "admin_title": "Formstack Med-liab Module",
                "link_title": "Medical and Emergency Contact Information",
                "module_type": "learn",
                "seq": 3,
                "required": True
                },
                {
                "admin_title": "Formstack Med-liab Bypass Page",
                "link_title": "Grant Medliab Bypass",
                "module_type": "manage",
                }]

    def isCompleted(self):
        return Record.user_completed(
                user=get_current_request().user,
                event="med",
                program=self.program) \
            or Record.user_completed(
                user=get_current_request().user,
                event="med_bypass",
                program=self.program)

    def students(self, QObject = False):
        Q_students = Q(record__event="med",
                       record__program=self.program)
        Q_bypass = Q(record__event="med_bypass",
                       record__program=self.program)


        if QObject:
            students = Q_students
            bypass = Q_bypass
        else:
            students = ESPUser.objects.filter(Q_students).distinct()
            bypass = ESPUser.objects.filter(Q_bypass).distinct()

        return {
            'studentmedliab': students,
            'studentmedbypass': bypass
            }

    def studentDesc(self):
        return {
            'studentmedliab': """Students who have completed their medliab online""",
            'studentmedbypass': """Students who have been granted a medliab bypass"""
            }

    @main_call
    @needs_student
    @meets_deadline('/FormstackMedliab')
    @meets_cap
    def medliab(self, request, tl, one, two, module, extra, prog):
        """
        Landing page redirecting to med-liab form on Formstack.
        """
        t = Tag.getTag("formstack_id", self.program)
        v = Tag.getTag("formstack_viewkey", self.program)
        context = {"formstack_id": t, "formstack_viewkey": v}
        return render_to_response(self.baseDir()+'medliab.html',
                                  request, context)

    @aux_call
    @needs_student
    def medicalpostback581309742(self, request, tl, one, two, module, extra, prog):
        """
        Marks student off as completed.
        """
        Record.objects.create(user=request.user, event="med", program=self.program)
        return self.goToCore(tl)

    @main_call
    @needs_admin
    def medicalbypass(self, request, tl, one, two, module, extra, prog):
        status = None
        
        if request.method == 'POST':
            form = GenericSearchForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['target_user']
                if Record.objects.filter(user=user,
                                          program=self.program,
                                          event="med_bypass").exists():
                    status = 'bypass exists'
                elif Record.objects.filter(user=user,
                                            program=self.program,
                                            event="med").exists():
                    status = 'reg bit exists'
                else:
                    Record.objects.create(user=user,
                                           program=self.program,
                                           event="med_bypass")
                    status = 'success'
            else:
                status = 'invalid user'

        context = {'status': status, 'form': GenericSearchForm()}

        return render_to_response(self.baseDir()+'medicalbypass.html',
                                  request, context)

    class Meta:
        proxy = True

