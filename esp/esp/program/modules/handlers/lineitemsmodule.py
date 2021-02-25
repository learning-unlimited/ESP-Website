
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
from esp.accounting.controllers import ProgramAccountingController
from esp.accounting.models import LineItemType, LineItemOptions
from esp.program.modules.base import ProgramModuleObj, needs_admin, CoreModule, main_call
from esp.program.modules.forms.lineitems import OptionFormset, LineItemForm, LineItemImportForm
from esp.utils.web import render_to_response

class LineItemsModule(ProgramModuleObj, CoreModule):

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Line Items Module",
            "link_title": "Line Items Management",
            "module_type": "manage",
            "seq": -9999,
            "choosable": 1,
            }

    @main_call
    @needs_admin
    def lineitems(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog, 'one': one, 'two': two}
        context['lineitems'] = prog.lineitemtype_set.all() # exclude ones that shouldn't be edited here
        context['option_formset'] = OptionFormset(queryset = LineItemOptions.objects.none(), prefix = "options")
        context['lineitem_form'] = LineItemForm()
        context['import_lineitem_form'] = LineItemImportForm(cur_prog = prog)
        
        if request.GET.get('op') == 'edit':
            line_item = LineItemType.objects.get(id=request.GET['id'])
            context['lineitem_form'] = LineItemForm(instance = line_item)
            context['option_formset'] = OptionFormset(queryset = line_item.lineitemoptions_set.all(), prefix='options')
        elif request.GET.get('op') == 'delete':
            line_item = LineItemType.objects.get(id=request.GET['id'])
            #render some page for confirmation
        elif request.method == 'POST':
            data = request.POST
            #process submitted form

        return render_to_response(self.baseDir()+'lineitems.html', request, context)

    def isStep(self):
        return True

    class Meta:
        proxy = True
        app_label = 'modules'
