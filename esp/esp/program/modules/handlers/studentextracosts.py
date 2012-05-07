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
from esp.users.models    import ESPUser, UserBit, User
from django.db.models.query import Q
from django.utils.safestring import mark_safe
from esp.datatree.sql.query_utils import QTree
from django.template.loader import get_template
from esp.program.models  import StudentApplication
from django              import forms
from django.contrib.auth.models import User
from esp.accounting_docs.models import Document
from esp.accounting_core.models import LineItem, LineItemType
from esp.middleware.threadlocalrequest import get_current_request
from collections import defaultdict

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

        print "Field ", required
        
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
    
    def get_invoice(self):
        return Document.get_invoice(get_current_request().user, self.program_anchor_cached(parent=True), [], dont_duplicate=True)

    def have_paid(self):
        return ( Document.objects.filter(user=get_current_request().user, anchor=self.program_anchor_cached(parent=True), txn__complete=True).count() > 0 )

    def studentDesc(self):
        """ Return a description for each line item type that students can be filtered by. """
        student_desc = {}
        treeq = QTree(anchor__below=self.program_anchor_cached(parent=True))
        for i in LineItemType.objects.filter(treeq):
            student_desc['extracosts_%d' % i.id] = """Students who have opted for '%s'""" % i.text

        return student_desc

    def students(self, QObject = False):
        """ Return the useful lists of students for the Extra Costs module. """

        student_lists = {}
        treeq = QTree(anchor__below=self.program_anchor_cached(parent=True))

        # Get all the line item types for this program.
        for i in LineItemType.objects.filter(treeq):
            if QObject:
                student_lists['extracosts_%d' % i.id] = self.getQForUser(Q(accounting_lineitem__li_type = i))
            else:
                student_lists['extracosts_%d' % i.id] = ESPUser.objects.filter(accounting_lineitem__li_type = i).distinct()

        return student_lists

    def isCompleted(self):
        return ( Document.objects.filter(user=get_current_request().user, anchor=self.program_anchor_cached(parent=True), txn__complete=True).count() > 0 or self.get_invoice().txn.lineitem_set.all().count() > 0 )

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

        #costs_list = set(LineItemType.forAnchor(prog.anchor).filter(optional=True).filter(lineitem__transaction__isnull=False, lineitem__user=request.user)) | set([x for x in LineItemType.forAnchor(prog.anchor).filter(optional=True) if x.lineitem_set.count() == 0])
        costs_list = LineItemType.objects.filter(anchor=GetNode(prog.anchor.get_uri()+'/LineItemTypes/Optional/BuyOne'))
        multicosts_list = LineItemType.objects.filter(anchor=GetNode(prog.anchor.get_uri()+'/LineItemTypes/Optional/BuyMany'))
        multiselect_list = LineItemType.objects.filter(anchor__parent__in=(GetNode(prog.anchor.get_uri()+'/LineItemTypes/Required/BuyMultiSelect'), GetNode(prog.anchor.get_uri()+'/LineItemTypes/Optional/BuyMultiSelect'))).select_related('anchor', 'anchor__parent__parent')

        multiselect_dict = defaultdict(list)
        for elt in multiselect_list:
            multiselect_dict[elt.anchor].append(elt)

        for lst in multiselect_dict.itervalues():
            lst.sort(key=lambda li: li.text)
        
        doc = self.get_invoice()

        def first_if_any(lst):
            try:
                return lst[0]
            except:
                return None

        ## Another dirty hack, left as an exercise to the reader
        if request.method == 'POST':
            costs_db = [ { 'LineItemType': x, 
                           'CostChoice': CostItem(request.POST, prefix="%s_" % x.id) }
                         for x in costs_list ] + \
                         [ x for x in \
                           [ { 'LineItemType': x, 
                               'CostChoice': MultiCostItem(request.POST, prefix="%s_" % x.id) }
                             for x in multicosts_list ] \
                           if x['CostChoice'].is_valid() and x['CostChoice'].cleaned_data.has_key('cost') ] + \
                           [ { 'LineItemType': l,
                               'CostChoice': MultiSelectCostItem(request.POST, prefix="multi%s_" % l.anchor.id,
                                                                 required=(l.anchor.parent.parent.name == 'Required'),
                                                                 choices=[(li.id, str(li.text)) for li in multiselect_dict[l.anchor]]) }
                             for l in multiselect_list ]

            for i in costs_db:
                if not i['CostChoice'].is_valid():
                    checked_ids = set( [ x.li_type_id for x in doc.txn.lineitem_set.all() ] )
                    li = None  ## Ugly hack, left as an exercise to the reader
                    forms = [ { 'form': CostItem( request.POST, prefix="%s_" % x.id, initial={'cost': (x.id in checked_ids ) } ),
                                'LineItem': x }
                              for x in costs_list ] + \
                              [ { 'form': MultiCostItem( request.POST, prefix="%s_" % x.id, initial={'cost': (x.id in checked_ids ), 'count': max(1, doc.txn.lineitem_set.filter(li_type=x).count()) } ),
                                  'LineItem': x }
                                for x in multicosts_list ] + \
                                [ { 'form': MultiSelectCostItem( request.POST, prefix="multi%s_" % anchor.id,
                                                                 initial={'cost': first_if_any(list(checked_ids.intersection(set(li.id for li in li_list))))},
                                                                 choices=[(li.id, str(li.text)) for li in li_list],
                                                                 required=(li.anchor.parent.parent.name == 'Required' if li else False)),
                                    'LineItem': {'text': anchor.name, 'description': mark_safe(anchor.friendly_name)} }
                                  for anchor, li_list in multiselect_dict.iteritems() ]
        

                    return render_to_response(self.baseDir()+'extracosts.html',
                                              request,
                                              (self.program, tl),
                                              { 'errors': True, 'forms': forms, 'financial_aid': ESPUser(request.user).hasFinancialAid(prog.anchor), 'select_qty': len(multicosts_list) > 0 })
                    break
                
                if i['CostChoice'].cleaned_data['cost'] and \
                       ((not isinstance(i['CostChoice'], MultiSelectCostItem)) or int(i['CostChoice'].cleaned_data['cost']) == i['LineItemType'].id):
                    if i['CostChoice'].cleaned_data.has_key('count'):
                        try:
                            count = int(i['CostChoice'].cleaned_data['count'])
                        except ValueError:
                            raise ESPError(True), "Error: Invalid cost value"
                    else:
                        count = 1

                    lis = doc.txn.lineitem_set.filter(li_type=i['LineItemType'])
                    lis_count = lis.count()

                    if lis_count > count:
                        for i in xrange(lis_count - count):
                            lis[i].delete()

                    if lis_count < count:
                        for c in xrange(count - lis_count):
                            doc.txn.add_item(request.user, i['LineItemType'], ESPUser(request.user).hasFinancialAid(prog.anchor))

                else:
                    doc.txn.lineitem_set.filter(li_type=i['LineItemType']).delete()

            return self.goToCore(tl)

        checked_ids = set( [ x.li_type_id for x in doc.txn.lineitem_set.all() ] )
        li = None  ## Ugly hack, left as an exercise to the reader
        forms = [ { 'form': CostItem( prefix="%s_" % x.id, initial={'cost': (x.id in checked_ids ) } ),
                    'LineItem': x }
                  for x in costs_list ] + \
                  [ { 'form': MultiCostItem( prefix="%s_" % x.id, initial={'cost': (x.id in checked_ids ), 'count': max(1, doc.txn.lineitem_set.filter(li_type=x).count()) } ),
                      'LineItem': x }
                    for x in multicosts_list ] + \
                    [ { 'form': MultiSelectCostItem( prefix="multi%s_" % anchor.id,
                                                     initial={'cost': first_if_any(list(checked_ids.intersection(set(li.id for li in li_list))))},
                                                     choices=[(li.id, str(li.text)) for li in li_list],
                                                     required=(li.anchor.parent.parent.name == 'Required' if li else False)),
                        'LineItem': {'text': anchor.name, 'description': mark_safe(anchor.friendly_name)} }
                      for anchor, li_list in multiselect_dict.iteritems() ]
        

        return render_to_response(self.baseDir()+'extracosts.html',
                                  request,
                                  (self.program, tl),
                                  { 'forms': forms, 'financial_aid': ESPUser(request.user).hasFinancialAid(prog.anchor), 'select_qty': len(multicosts_list) > 0 })


    class Meta:
        abstract = True

