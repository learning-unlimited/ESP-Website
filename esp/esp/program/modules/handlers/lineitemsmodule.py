
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
from esp.accounting.models import LineItemType, LineItemOptions
from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj, needs_admin, CoreModule, main_call
from esp.program.modules.forms.lineitems import OptionFormset, LineItemForm, LineItemImportForm, exclude_line_items
from esp.utils.web import render_to_response

class LineItemsModule(ProgramModuleObj, CoreModule):
    doc = """Create and/or edit line items for the program."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Line Items Module",
            "link_title": "Line Items Management",
            "module_type": "manage",
            "seq": -9999,
            "choosable": 0,
            }

    @main_call
    @needs_admin
    def lineitems(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog, 'one': one, 'two': two}

        if request.GET.get('op') == 'edit':
            # load selected line item type in form
            lineitem = LineItemType.objects.get(id=request.GET['id'])
            context['lineitem'] = lineitem
            context['lineitem_form'] = LineItemForm(instance = lineitem)
            context['option_formset'] = OptionFormset(queryset = lineitem.lineitemoptions_set.all(), prefix='options')
        elif request.GET.get('op') == 'delete':
            # show delete confirmation page
            context['lineitem'] = LineItemType.objects.get(id=request.GET['id'])
            return render_to_response(self.baseDir()+'lineitem_delete.html', request, context)
        elif request.GET.get('op') == 'import':
            # show import confirmation page
            import_form = LineItemImportForm(request.POST, cur_prog = prog)
            if not import_form.is_valid():
                context['import_lineitem_form'] = import_form
            else:
                past_program = import_form.cleaned_data['program']
                context['past_program'] = past_program
                context['lineitems'] = past_program.lineitemtype_set.exclude(text__in=exclude_line_items)
                return render_to_response(self.baseDir()+'lineitem_import.html', request, context)
        elif request.method == 'POST':
            if request.POST.get('command') == 'reallyremove':
                # deletion confirmed
                lineitem = LineItemType.objects.get(id=request.POST['id'])
                lineitem.lineitemoptions_set.all().delete()
                lineitem.delete()
            elif request.POST.get('command') == 'reallyimport':
                # import confirmed
                past_program = Program.objects.get(id=request.POST['program'])
                past_lineitems = past_program.lineitemtype_set.exclude(text__in=exclude_line_items)
                for past_lineitem in past_lineitems:
                    old_options = past_lineitem.lineitemoptions_set.all()
                    past_lineitem.pk = None
                    past_lineitem.program = prog
                    past_lineitem.save()
                    for old_option in old_options:
                        old_option.pk = None
                        old_option.lineitem_type = past_lineitem
                        old_option.save()
            elif request.POST.get('command') == 'addedit':
                # addedit form submitted
                if 'id_lineitem' in request.POST:
                    lineitem_form = LineItemForm(request.POST, instance = LineItemType.objects.get(id=request.POST['id_lineitem']))
                else:
                    lineitem_form = LineItemForm(request.POST)
                options_formset = OptionFormset(request.POST, prefix='options')
                if lineitem_form.is_valid() and options_formset.is_valid():
                    if LineItemType.objects.filter(text = lineitem_form.cleaned_data['text'], program = prog).exists() and 'id_lineitem' not in request.POST:
                        lineitem_form.add_error('text', 'A line item with that name already exists. Please choose another name.')
                        context['lineitem_form'] = lineitem_form
                        context['option_formset'] = options_formset
                    else:
                        # first save the line item, as its reference will be used for the line item options
                        lineitem = lineitem_form.save(commit = False)
                        lineitem.program = prog
                        lineitem.save()
                        for options_form in options_formset:
                            # save and attach each option to the line item
                            option = options_form.save(commit=False)
                            option.lineitem_type = lineitem
                            option.save()
                else:
                    context['lineitem_form'] = lineitem_form
                    context['option_formset'] = options_formset
        if 'lineitem_form' not in context:
            context['lineitem_form'] = LineItemForm()
        if 'option_formset' not in context:
            context['option_formset'] = OptionFormset(queryset = LineItemOptions.objects.none(), prefix = "options")
        if 'import_lineitem_form' not in context:
            context['import_lineitem_form'] = LineItemImportForm(cur_prog = prog)
        context['lineitems'] = prog.lineitemtype_set.exclude(text__in=exclude_line_items)# exclude ones that shouldn't be edited here

        return render_to_response(self.baseDir()+'lineitems.html', request, context)

    def isStep(self):
        return self.program.hasModule("StudentExtraCosts")

    setup_title = "Set up custom items for purchase"

    def isCompleted(self):
        return self.program.lineitemtype_set.exclude(text__in=exclude_line_items).exists()

    class Meta:
        proxy = True
        app_label = 'modules'
