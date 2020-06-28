
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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

import logging
logger = logging.getLogger(__name__)

from django.db.models.query import Q
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, meets_any_deadline, main_call, aux_call
from esp.utils.web import render_to_response
from esp.users.models    import ESPUser
from esp.application.models import FormstackStudentProgramApp
from urllib import urlencode

class FormstackAppModule(ProgramModuleObj):
    """
    Student application module for Junction.

    Not to be confused with StudentJunctionAppModule, the app questions module.
    """

    @classmethod
    def module_properties(cls):
        return [{
            "admin_title": "Formstack Application Module",
            "link_title": "Student Application",
            "module_type": "learn",
            "seq": 10,
            "required": True,
            "choosable": 2,
            }]

    def students(self, QObject = False):
        result = {}

        Q_applied = Q(studentprogramapp__program=self.program)
        result['applied'] = Q_applied if QObject else ESPUser.objects.filter(Q_applied)

        return result

    def studentDesc(self):
        result = {}
        result['applied'] = """Students who submitted an application"""
        return result

    def isCompleted(self):
        # TODO
        return False

    @main_call
    @needs_student
    def studentapp(self, request, tl, one, two, module, extra, prog):
        fsas = prog.formstackappsettings
        context = {}
        context['form'] = fsas.form()
        context['username_field'] = fsas.username_field
        context['username'] = request.user.username
        context['app_is_open'] = fsas.app_is_open or request.user.isAdmin(prog)
        context['autopopulated'] = autopopulated = []
        for line in fsas.autopopulated_fields.strip().split('\n'):
            field, _, expr = line.partition(':')
            try:
                value = eval(expr, {'user': request.user})
            except Exception as e:
                logger.exception("Error in FormstackAppSettings: %s", e)
                continue
            autopopulated.append((field, value))
        return render_to_response(self.baseDir()+'studentapp.html',
                                  request, context)

    @aux_call
    @needs_student
    def finaidapp(self, request, tl, one, two, module, extra, prog):
        fsas = prog.formstackappsettings
        if not fsas.finaid_form():
            return # no finaid form
        app = FormstackStudentProgramApp.objects.filter(user=request.user, program=prog)
        if not (app or request.user.isAdmin(prog)): # student has not applied for the program
            return # XXX: more useful error here
        context = {}
        context['form'] = fsas.finaid_form()
        context['user_id_field'] = fsas.finaid_user_id_field
        context['user_id'] = request.user.id
        context['username_field'] = fsas.finaid_username_field
        context['username'] = request.user.username
        return render_to_response(self.baseDir()+'finaidapp.html',
                                  request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
