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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.datatree.models import *
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser
from django.db.models.query import Q
from django.utils.safestring import mark_safe
from django.template.loader import get_template
from esp.program.models  import StudentApplication
from django              import forms
from django.contrib.auth.models import User
from esp.accounting_core.models import LineItemType
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
    cost = forms.ChoiceField(required=False, label='', widget=forms.RadioSelect, choices=[])
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices')
        required = kwargs.pop('required')
        super(MultiSelectCostItem, self).__init__(*args, **kwargs)
        self.fields['cost'].choices = choices
        self.fields['cost'].required = required

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

    def have_paid(self):
        iac = IndividualAccountingController(self.program, get_current_request().user)
        return (iac.amount_due() <= 0)

    def studentDesc(self):
        """ Return a description for each line item type that students can be filtered by. """
        student_desc = {}
        pac = ProgramAccountingController(self.program)
        for i in pac.get_lineitemtypes(optional_only=True):
            student_desc['extracosts_%d' % i.id] = """Students who have opted for '%s'""" % i.text

        return student_desc

    def students(self, QObject = False):
        """ Return the useful lists of students for the Extra Costs module. """

        student_lists = {}
        pac = ProgramAccountingController(self.program)
        
        # Get all the line item types for this program.
        for i in pac.get_lineitemtypes(optional_only=True):
            if QObject:
                student_lists['extracosts_%d' % i.id] = self.getQForUser(Q(transfer__line_item = i))
            else:
                student_lists['extracosts_%d' % i.id] = ESPUser.objects.filter(transfer__line_item = i).distinct()

        return student_lists

    def isCompleted(self):
        iac = IndividualAccountingController(self.program, get_current_request().user)
        return (len(iac.get_preferences()) > 0)

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
            raise ESPError(False), "You've already paid for this program; you can't pay again!"

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
                                                     choices=x.options_str,
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
                            form_prefs.append((lineitem_type.text, 1, lineitem_type.amount))
                    elif isinstance(form, MultiCostItem):
                        if form.cleaned_data['cost'] is True:
                            form_prefs.append((lineitem_type.text, form.cleaned_data['count'], lineitem_type.amount))
                    elif isinstance(form, MultiSelectCostItem):
                        if form.cleaned_data['cost']:
                            form_prefs.append((lineitem_type.text, 1, Decimal(form.cleaned_data['cost'])))
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
                return self.goToCore(tl)

        count_map = {}
        for lineitem_type in iac.get_lineitemtypes(optional_only=True):
            count_map[lineitem_type.text] = [lineitem_type.id, 0, None]
        for item in iac.get_preferences():
            count_map[item[0]][1] = item[1]
            count_map[item[0]][2] = item[2]
        forms = [ { 'form': CostItem( prefix="%s" % x.id, initial={'cost': (count_map[x.text][1] > 0) } ),
                    'LineItem': x }
                  for x in costs_list ] + \
                  [ { 'form': MultiCostItem( prefix="%s" % x.id, initial={'cost': (count_map[x.text][1] > 0), 'count': count_map[x.text][1] } ),
                      'LineItem': x }
                    for x in multicosts_list ] + \
                    [ { 'form': MultiSelectCostItem( prefix="multi%s" % x.id,
                                                     initial={'cost': (('%.2f' % count_map[x.text][2]) if count_map[x.text][2] else None)},
                                                     choices=x.options_str,
                                                     required=(x.required)),
                        'LineItem': x }
                      for x in multiselect_list ]

        return render_to_response(self.baseDir()+'extracosts.html',
                                  request,
                                  { 'errors': not forms_all_valid, 'forms': forms, 'financial_aid': ESPUser(request.user).hasFinancialAid(prog), 'select_qty': len(multicosts_list) > 0 })


    class Meta:
        abstract = True

