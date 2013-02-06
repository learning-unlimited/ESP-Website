
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
  Email: web-team@lists.learningu.org
"""

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import *
from django              import forms
from django.http import HttpResponseRedirect
from esp.users.views    import search_for_user
from esp.accounting_docs.models   import Document
from esp.accounting_core.models   import LineItemType


class OnsitePaidItemsModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Onsite View Purchased Items",
            "link_title": "View Purchased Items for a Student",
            "module_type": "onsite",
            "seq": 31
            }

    @main_call
    @needs_onsite
    def paiditems(self, request, tl, one, two, module, extra, prog):

        user, found = search_for_user(request, self.program.students_union())
        if not found:
            return user

        context = {}
        context['student'] = user
        context['program'] = prog

        li_types = prog.getLineItemTypes(user)

        try:
            invoice = Document.get_invoice(user, prog.anchor, li_types, dont_duplicate=True, get_complete=True)
        except:
            invoice = Document.get_invoice(user, prog.anchor, li_types, dont_duplicate=True)

        context['reserveditems'] = invoice.get_items()
        context['cost'] = invoice.cost()
        
        return render_to_response(self.baseDir()+'paiditems.html', request, (prog, tl), context)


    class Meta:
        abstract = True

