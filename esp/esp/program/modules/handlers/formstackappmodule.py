
__author__ = "Individual contributors (see AUTHORS file)"
__date__ = "$DATE$"
__rev__ = "$REV$"
__license__ = "AGPL v.3"
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

from django.db.models.query import Q
from django.template import Variable, Context, VariableDoesNotExist

from esp.application.models import FormstackStudentProgramApp
from esp.program.modules.base import (
    ProgramModuleObj, needs_student_in_grade, main_call, aux_call
)
from esp.users.models import ESPUser
from esp.utils.web import render_to_response

logger = logging.getLogger(__name__)


def resolve_field_expression(expression, context_vars):
    """Safely resolve a dotted expression against the given context.

    Returns the string value, or None if the expression is empty,
    whitespace-only, unresolvable, or resolves to None.
    """
    if not expression or not expression.strip():
        return None
    expression = expression.strip()
    try:
        resolved = Variable(expression).resolve(Context(context_vars))
        if resolved is None:
            return None
        return str(resolved)
    except VariableDoesNotExist:
        return None
    except Exception:
        logger.exception(
            "Error resolving field expression '%s'", expression
        )
        return None


class FormstackAppModule(ProgramModuleObj):
    doc = """
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

    def students(self, QObject=False):
        result = {}

        Q_applied = Q(studentprogramapp__program=self.program)
        if QObject:
            result['applied'] = Q_applied
        else:
            result['applied'] = ESPUser.objects.filter(Q_applied)

        return result

    def studentDesc(self):
        result = {}
        result['applied'] = """Students who submitted an application"""
        return result

    def isCompleted(self):
        # TODO
        return False

    @main_call
    @needs_student_in_grade
    def studentapp(self, request, tl, one, two, module, extra, prog):
        fsas = prog.formstackappsettings
        context = {}
        context['form'] = fsas.form()
        context['username_field'] = fsas.username_field
        context['username'] = request.user.username
        context['app_is_open'] = fsas.app_is_open or request.user.isAdmin(prog)
        context['autopopulated'] = autopopulated = []
        for line in fsas.autopopulated_fields.strip().split('\n'):
            if not line.strip():
                continue
            field, _, expr = line.partition(':')
            value = resolve_field_expression(expr, {'user': request.user})
            field_name = field.strip()
            if value is not None and field_name:
                autopopulated.append((field_name, value))
        return render_to_response(self.baseDir()+'studentapp.html',
                                  request, context)

    @aux_call
    @needs_student_in_grade
    def finaidapp(self, request, tl, one, two, module, extra, prog):
        fsas = prog.formstackappsettings
        if not fsas.finaid_form():
            return self.goToCore(tl)  # no finaid form
        app = FormstackStudentProgramApp.objects.filter(
            user=request.user, program=prog
        )
        # student has not applied for the program
        if not (app or request.user.isAdmin(prog)):
            return  # XXX: more useful error here
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
