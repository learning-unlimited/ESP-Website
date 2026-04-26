from __future__ import absolute_import
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

from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.users.forms.generic_search_form import StudentSearchForm
from esp.utils.web import render_to_response
from esp.accounting.views import user_accounting
from esp.users.models import ESPUser

class AccountingModule(ProgramModuleObj):
    doc = """Lists accounting information for the program for a single user."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Accounting",
            "link_title": "Accounting",
            "module_type": "manage",
            "seq": 253,
            "choosable": 0,
            }

    @main_call
    @needs_admin
    def accounting(self, request, tl, one, two, module, extra, prog):
        user = None
        context = {}
        if extra:
            user = ESPUser.objects.get(id=extra)
        elif 'target_user' in request.POST:
            form = StudentSearchForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['target_user']
        else:
            form = StudentSearchForm()

        if user:
            form = StudentSearchForm(initial={'target_user': user.id})
            context['prog_results'] = user_accounting(user, [prog])

        context['target_user'] = user
        context['form'] = form
        return render_to_response(self.baseDir()+'accounting.html', request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
