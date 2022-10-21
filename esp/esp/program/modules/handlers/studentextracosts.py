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
from collections import OrderedDict, defaultdict
from decimal import Decimal
from django              import forms
from django.db.models.query import Q
from django.utils.safestring import mark_safe
from esp.accounting.controllers import IndividualAccountingController, ProgramAccountingController
from esp.accounting.models import LineItemOptions
from esp.middleware      import ESPError
from esp.middleware.threadlocalrequest import get_current_request
from esp.program.models  import StudentApplication, SplashInfo
from esp.program.modules.base import ProgramModuleObj, needs_student, meets_deadline, main_call, meets_cap
from esp.program.modules.forms.splashinfo import SiblingDiscountForm
from esp.users.models    import Record, RecordType
from esp.utils.web import render_to_response
from esp.utils.widgets import ChoiceWithOtherField

class CostItem(forms.Form):
    def __init__(self, *args, **kwargs):
        required = kwargs.pop('required', False)
        super(CostItem, self).__init__(*args, **kwargs)
        self.fields['cost'] = forms.BooleanField(required=required, label='')

class MultiCostItem(forms.Form):
    def __init__(self, *args, **kwargs):
        required = kwargs.pop('required', False)
        max_quantity = kwargs.pop('max_quantity', 10)
        min_quantity = 1 if required else 0
        super(MultiCostItem, self).__init__(*args, **kwargs)
        self.fields['count'] = forms.IntegerField(required=required, initial=min_quantity, max_value=max_quantity, min_value=min_quantity, widget=forms.NumberInput(attrs={'class': 'input-mini'}))

class MultiSelectCostItem(forms.Form):
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        required = kwargs.pop('required')
        is_custom = kwargs.pop('is_custom', False)
        super(MultiSelectCostItem, self).__init__(*args, **kwargs)
        if is_custom:
            self.fields['option'] = ChoiceWithOtherField(required=required, label='', choices=choices)
        else:
            self.fields['option'] = forms.ChoiceField(required=required, label='', choices=choices, widget=forms.RadioSelect)

# pick extra items to buy for each program
class StudentExtraCosts(ProgramModuleObj):
    doc = """Serves a form during student registration for students to purchase other items."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Optional Fees",
            "link_title": "T-Shirts, Meals, and Photos",
            "module_type": "learn",
            "seq": 30,
            "choosable": 0,
            }

    def __init__(self, *args, **kwargs):
        super(StudentExtraCosts, self).__init__(*args, **kwargs)
        self.event = "extra_costs_done"

    def studentDesc(self):
        """ Return a description for each line item type that students can be filtered by. """
        student_desc = {}
        pac = ProgramAccountingController(self.program)
        for line_item_type in pac.get_lineitemtypes(include_donations=False):
            student_desc['extracosts_%d' % line_item_type.id] = """Students who have opted for '%s'""" % line_item_type.text
            for option in line_item_type.options:
                (option_id, option_amount, option_description, has_custom_amt) = option
                key = 'extracosts_%d_%d' % (line_item_type.id, option_id)
                student_desc[key] = """Students who have opted for '%s' for '%s' ($%s)""" % (option_description, line_item_type.text, option_amount or line_item_type.amount_dec)
        if self.program.sibling_discount:
            student_desc['sibling_discount'] = """Students who have opted for a sibling discount"""

        return student_desc

    def students(self, QObject = False):
        """ Return the useful lists of students for the Extra Costs module. """

        student_lists = OrderedDict()
        pac = ProgramAccountingController(self.program)

        # Get all the line item types for this program.
        for i in pac.get_lineitemtypes(include_donations=False):
            if QObject:
                students = pac.all_students_Q(lineitemtype_id=i.id)
                student_lists['extracosts_%d' % i.id] = students
            else:
                students = pac.all_students(lineitemtype_id=i.id).distinct()
                student_lists['extracosts_%d' % i.id] = students
            for option in i.options:
                key = 'extracosts_%d_%d' % (i.id, option[0])
                filter_qobject = Q(transfer__option=option[0])
                if QObject:
                    student_lists[key] = students & filter_qobject
                else:
                    student_lists[key] = students.filter(filter_qobject).distinct()
        if self.program.sibling_discount:
            sibling_line_item = pac.default_siblingdiscount_lineitemtype()
            if QObject:
                student_lists['sibling_discount'] = pac.all_students_Q(lineitemtype_id=sibling_line_item.id)
            else:
                student_lists['sibling_discount'] = pac.all_students(lineitemtype_id=sibling_line_item.id).distinct()

        return student_lists

    def isCompleted(self):
        if hasattr(self, 'user'):
            user = self.user
        else:
            user = get_current_request().user
        return Record.objects.filter(user=user, program=self.program, event__name=self.event).exists()

    def lineitemtypes(self):
        pac = ProgramAccountingController(self.program)
        return pac.get_lineitemtypes(include_donations=False).exclude(text__in=pac.admission_items)

    @main_call
    @needs_student
    @meets_deadline('/ExtraCosts')
    @meets_cap
    def extracosts(self,request, tl, one, two, module, extra, prog):
        """
        Query the user for any extra items they may wish to purchase for this program

        This module should ultimately deal with things like optional lab fees, etc.
        Right now it doesn't.
        """
        iac = IndividualAccountingController(self.program, request.user)
        if iac.has_paid():
            raise ESPError("You've already paid for this program.  Please make any further changes onsite so that we can charge or refund you properly.", log=False)

        #   Determine which line item types we will be asking about
        costs_list = self.lineitemtypes().filter(max_quantity__lte=1, lineitemoptions__isnull=True)
        multicosts_list = self.lineitemtypes().filter(max_quantity__gt=1, lineitemoptions__isnull=True)
        multiselect_list = self.lineitemtypes().filter(lineitemoptions__isnull=False)
        if prog.sibling_discount:
            sibling_line_item = iac.default_siblingdiscount_lineitemtype()
            sibling_form = SiblingDiscountForm(prefix="%s" % sibling_line_item.id, program=prog)
            spi = SplashInfo.getForUser(request.user, self.program)
            sibling_form.load(spi)

        #   Fetch the user's current preferences
        prefs = iac.get_preferences()

        forms_all_valid = True
        error_custom = False
        preserve_items = {}

        ## Another dirty hack, left as an exercise to the reader
        if request.method == 'POST':

            #   Initialize a list of forms using the POST data
            costs_db = [ { 'LineItemType': x,
                           'CostChoice': CostItem(request.POST, prefix="%s" % x.id,
                                                  required=(x.required)) }
                         for x in costs_list ] + \
                           [ { 'LineItemType': x,
                               'CostChoice': MultiCostItem(request.POST, prefix="%s" % x.id,
                                                           required=(x.required),
                                                           max_quantity=(x.max_quantity))}
                             for x in multicosts_list ] + \
                           [ { 'LineItemType': x,
                               'CostChoice': MultiSelectCostItem(request.POST, prefix="multi%s" % x.id,
                                                                 choices=x.option_choices,
                                                                 required=(x.required),
                                                                 is_custom=(x.has_custom_options)) }
                             for x in multiselect_list ]
            if prog.sibling_discount:
                sibling_form = SiblingDiscountForm(request.POST, prefix="%s" % sibling_line_item.id, program=prog)
                costs_db.append({'LineItemType': sibling_line_item, 'CostChoice': sibling_form})

            #   Get a list of the (line item, quantity) pairs stored in the forms
            #   as well as a list of line items which had invalid forms
            form_prefs = []

            for item in costs_db:
                form = item['CostChoice']
                lineitem_type = item['LineItemType']

                if form.is_valid():
                    if isinstance(form, CostItem):
                        if form.cleaned_data['cost'] is True:
                            form_prefs.append((lineitem_type.text, 1, lineitem_type.amount, None))

                    elif isinstance(form, MultiCostItem):
                        form_prefs.append((lineitem_type.text, form.cleaned_data['count'] or 0, lineitem_type.amount, None))

                    elif isinstance(form, MultiSelectCostItem):
                        if form.cleaned_data['option']:
                            if lineitem_type.has_custom_options:
                                option_id, option_amount = form.cleaned_data['option']
                            else:
                                option_id = form.cleaned_data['option']
                                option_amount = None
                            if option_id:
                                option = LineItemOptions.objects.get(id=option_id)
                                #   Give error if no amount was typed in
                                if option.is_custom and not option_amount:
                                    preserve_items.append(lineitem_type.text)
                                    forms_all_valid = False
                                    error_custom = True
                                else:
                                    #   Use default amount if this option doesn't allow a custom amount
                                    if not option.is_custom:
                                        option_amount = option.amount_dec_inherited
                                    form_prefs.append((lineitem_type.text, 1, float(option_amount), int(option_id)))

                    elif isinstance(form, SiblingDiscountForm):
                        form.save(spi)
                else:
                    #   Preserve selected quantity for any items that we don't have a valid form for
                    preserve_items[lineitem_type.text] = form
                    forms_all_valid = False

            #   Merge previous and new preferences (update only if the form was valid)
            new_prefs = []
            for lineitem_name in preserve_items.keys():
                if lineitem_name in map(lambda x: x[0], prefs):
                    new_prefs.append(prefs[map(lambda x: x[0], prefs).index(lineitem_name)])

            new_prefs += form_prefs
            iac.apply_preferences(new_prefs)

            #   Redirect to main student reg page if all data was recorded properly
            #   (otherwise, the code below will reload the page)
            if forms_all_valid:
                rt = RecordType.objects.get(name=self.event)
                bit, created = Record.objects.get_or_create(user=request.user, program=self.program, event=rt)
                return self.goToCore(tl)

            ### End Post

        count_map = {}
        for lineitem_type in self.lineitemtypes():
            count_map[lineitem_type.text] = [lineitem_type.id, 1 if lineitem_type.required else 0, None, None]

        for item in iac.get_preferences(self.lineitemtypes()):
            for i in range(1, 4):
                count_map[item[0]][i] = item[i]

        cost_items =  \
        [
            {
               'form': preserve_items.get(x.text) or CostItem( prefix="%s" % x.id,
                                                               initial={'cost': (count_map[x.text][1] > 0) },
                                                               required=(x.required) ),
               'type': 'single',
               'LineItem': x
            }

            for x in costs_list
        ]

        multi_cost_items = \
        [
            {
                'form': preserve_items.get(x.text) or MultiCostItem( prefix="%s" % x.id,
                                                                     initial={'count': count_map[x.text][1] },
                                                                     required=(x.required),
                                                                     max_quantity=(x.max_quantity) ),
                'type': 'multiple',
                'LineItem': x
            }

            for x in multicosts_list
        ]

        multiselect_costitems = []
        for x in multiselect_list:
            new_entry = {'type': 'select', 'LineItem': x}
            form_kwargs = {'prefix': "multi%s" % x.id, 'choices': x.option_choices, 'required': x.required}
            if x.has_custom_options:
                #   Provide an initial value for a custom amount if an option has been selected
                #   and the saved amount differs from the amount this option would normally cost.
                custom_amount = ''
                if count_map[x.text][3]:
                    default_amount = LineItemOptions.objects.get(id=count_map[x.text][3]).amount_dec_inherited
                    if count_map[x.text][2] != default_amount:
                        custom_amount = count_map[x.text][2]
                form_kwargs['initial'] = {'option': (count_map[x.text][3], custom_amount)}
                form_kwargs['is_custom'] = True
            else:
                form_kwargs['initial'] = {'option': count_map[x.text][3]}
                form_kwargs['is_custom'] = False
            new_entry['form'] = preserve_items.get(x.text) or MultiSelectCostItem(**form_kwargs)
            multiselect_costitems.append(new_entry)

        forms = cost_items + multi_cost_items + multiselect_costitems
        if prog.sibling_discount:
            forms.append({
                    'form': sibling_form,
                    'type': 'sibling',
                    'LineItem': sibling_line_item
                })

        return render_to_response(self.baseDir()+'extracosts.html',
                                  request,
                                  { 'errors': not forms_all_valid, 'error_custom': error_custom, 'forms': forms, 'financial_aid': request.user.hasFinancialAid(prog), 'select_qty': len(multicosts_list) > 0 })

    def isStep(self):
        return self.lineitemtypes().exists()

    def isRequired(self):
        return self.lineitemtypes().filter(required=True).exists()

    class Meta:
        proxy = True
        app_label = 'modules'
