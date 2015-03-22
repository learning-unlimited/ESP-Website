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
from collections import OrderedDict

from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.datatree.models import *
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, Record
from django.db.models.query import Q
from django.utils.safestring import mark_safe
from django.template.loader import get_template
from esp.program.models  import StudentApplication
from django              import forms
from django.contrib.auth.models import User
from esp.accounting.controllers import IndividualAccountingController, ProgramAccountingController
from esp.middleware.threadlocalrequest import get_current_request
from collections import defaultdict

from decimal import Decimal

class CostItem(forms.Form):
    cost = forms.BooleanField(required=False, label='')

class MultiCostItem(forms.Form):
    cost = forms.BooleanField(required=False, label='')
    count = forms.IntegerField(max_value=10, min_value=0)

class MultiSelectCostItem(forms.Form):
    option = forms.ChoiceField(required=False, label='', widget=forms.RadioSelect, choices=[])
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        required = kwargs.pop('required')
        super(MultiSelectCostItem, self).__init__(*args, **kwargs)
        self.fields['option'].choices = choices
        self.fields['option'].required = required

# pick extra items to buy for each program
class StudentExtraCosts(ProgramModuleObj):

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Optional Fees",
            "link_title": "T-Shirts, Meals, and Photos",
            "module_type": "learn",
            "seq": 30
            }

    def __init__(self, *args, **kwargs):
        super(StudentExtraCosts, self).__init__(*args, **kwargs)
        self.event = "extra_costs_done"

    def have_paid(self):
        iac = IndividualAccountingController(self.program, get_current_request().user)
        return (iac.amount_due() <= 0)

    def studentDesc(self):
        """ Return a description for each line item type that students can be filtered by. """
        student_desc = {}
        pac = ProgramAccountingController(self.program)
        for line_item_type in pac.get_lineitemtypes(optional_only=True):
            student_desc['extracosts_%d' % line_item_type.id] = """Students who have opted for '%s'""" % line_item_type.text
            for option in line_item_type.options:
                (option_id, option_amount, option_description) = option
                key = 'extracosts_%d_%d' % (line_item_type.id, option_id)
                student_desc[key] = """Students who have opted for '%s' for '%s' ($%s)""" % (option_description, line_item_type.text, option_amount or line_item_type.amount_dec)

        return student_desc

    def students(self, QObject = False):
        """ Return the useful lists of students for the Extra Costs module. """

        student_lists = OrderedDict()
        pac = ProgramAccountingController(self.program)
        
        # Get all the line item types for this program.
        for i in pac.get_lineitemtypes(optional_only=True):
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

        return student_lists

    def isCompleted(self):
        return Record.objects.filter(user=get_current_request().user, program=self.program, event=self.event).exists()

    @main_call
    @needs_student
    @meets_deadline('/ExtraCosts')
    def extracosts(self,request, tl, one, two, module, extra, prog):
        """
        Query the user for any extra items they may wish to purchase for this program

        This module should ultimately deal with things like optional lab fees, etc.
        Right now it doesn't.
        """
        if self.have_paid():
            raise ESPError("You've already paid for this program.  Please make any further changes on-site so that we can charge or refund you properly.", log=False)

        #   Determine which line item types we will be asking about
        iac = IndividualAccountingController(self.program, get_current_request().user)
        costs_list = iac.get_lineitemtypes(optional_only=True).filter(max_quantity__lte=1, lineitemoptions__isnull=True)
        multicosts_list = iac.get_lineitemtypes(optional_only=True).filter(max_quantity__gt=1, lineitemoptions__isnull=True)
        multiselect_list = iac.get_lineitemtypes(optional_only=True).filter(lineitemoptions__isnull=False)

        #   Fetch the user's current preferences
        prefs = iac.get_preferences()

        forms_all_valid = True

        ## Another dirty hack, left as an exercise to the reader
        if request.method == 'POST':

            #   Initialize a list of forms using the POST data
            costs_db = [ { 'LineItemType': x, 
                           'CostChoice': CostItem(request.POST, prefix="%s" % x.id) }
                         for x in costs_list ] + \
                         [ x for x in \
                           [ { 'LineItemType': x, 
                               'CostChoice': MultiCostItem(request.POST, prefix="%s" % x.id) }
                             for x in multicosts_list ] \
                           if x['CostChoice'].is_valid() and x['CostChoice'].cleaned_data.has_key('cost') ] + \
                           [ { 'LineItemType': x,
                               'CostChoice': MultiSelectCostItem(request.POST, prefix="multi%s" % x.id,
                                                     choices=x.option_choices,
                                                     required=(x.required)) }
                             for x in multiselect_list ]

            #   Get a list of the (line item, quantity) pairs stored in the forms
            #   as well as a list of line items which had invalid forms
            form_prefs = []
            preserve_items = []
            for item in costs_db:
                form = item['CostChoice']
                lineitem_type = item['LineItemType']
                if form.is_valid():
                    if isinstance(form, CostItem):
                        if form.cleaned_data['cost'] is True:
                            form_prefs.append((lineitem_type.text, 1, lineitem_type.amount, None))
                    elif isinstance(form, MultiCostItem):
                        if form.cleaned_data['cost'] is True:
                            form_prefs.append((lineitem_type.text, form.cleaned_data['count'], lineitem_type.amount, None))
                    elif isinstance(form, MultiSelectCostItem):
                        if form.cleaned_data['option']:
                            form_prefs.append((lineitem_type.text, 1, None, int(form.cleaned_data['option'])))
                else:
                    #   Preserve selected quantity for any items that we don't have a valid form for
                    preserve_items.append(lineitem_type.text)
                    forms_all_valid = False

            #   Merge previous and new preferences (update only if the form was valid)
            new_prefs = []
            for lineitem_name in preserve_items:
                if lineitem_name in map(lambda x: x[0], prefs):
                    new_prefs.append(prefs[map(lambda x: x[0], prefs).index(lineitem_name)])
            new_prefs += form_prefs

            iac.apply_preferences(new_prefs)

            #   Redirect to main student reg page if all data was recorded properly
            #   (otherwise, the code below will reload the page)
            if forms_all_valid:
                bit, created = Record.objects.get_or_create(user=request.user, program=self.program, event=self.event)
                return self.goToCore(tl)

        count_map = {}
        for lineitem_type in iac.get_lineitemtypes(optional_only=True):
            count_map[lineitem_type.text] = [lineitem_type.id, 0, None, None]
        for item in iac.get_preferences():
            for i in range(1, 4):
                count_map[item[0]][i] = item[i]
        forms = [ { 'form': CostItem( prefix="%s" % x.id, initial={'cost': (count_map[x.text][1] > 0) } ),
                    'LineItem': x }
                  for x in costs_list ] + \
                  [ { 'form': MultiCostItem( prefix="%s" % x.id, initial={'cost': (count_map[x.text][1] > 0), 'count': count_map[x.text][1] } ),
                      'LineItem': x }
                    for x in multicosts_list ] + \
                    [ { 'form': MultiSelectCostItem( prefix="multi%s" % x.id,
                                                     initial={'option': count_map[x.text][3]},
                                                     choices=x.option_choices,
                                                     required=(x.required)),
                        'LineItem': x }
                      for x in multiselect_list ]

        return render_to_response(self.baseDir()+'extracosts.html',
                                  request,
                                  { 'errors': not forms_all_valid, 'forms': forms, 'financial_aid': ESPUser(request.user).hasFinancialAid(prog), 'select_qty': len(multicosts_list) > 0 })


    class Meta:
        proxy = True

