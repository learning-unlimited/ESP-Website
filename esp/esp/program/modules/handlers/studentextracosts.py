__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, main_call, aux_call
from esp.datatree.models import GetNode, DataTree
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, UserBit, User
from django.db.models.query import Q
from django.template.loader import get_template
from esp.program.models  import StudentApplication
from django              import forms
from django.contrib.auth.models import User
from esp.accounting_docs.models import Document
from esp.accounting_core.models import LineItem, LineItemType


class CostItem(forms.Form):
    cost = forms.BooleanField(required=False, label='')

class MultiCostItem(forms.Form):
    cost = forms.BooleanField(required=False, label='')
    count = forms.IntegerField(max_value=10, min_value=0)

# pick extra items to buy for each program
class StudentExtraCosts(ProgramModuleObj):

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "T-Shirts",
            "module_type": "learn",
            "seq": 30
            }
    
    def get_invoice(self):
        return Document.get_invoice(self.user, self.program_anchor_cached(parent=True), [], dont_duplicate=True)

    def have_paid(self):
        return ( Document.objects.filter(user=self.user, anchor=self.program_anchor_cached(parent=True), txn__complete=True).count() > 0 )

    def studentDesc(self):
        """ Return a description for each line item type that students can be filtered by. """
        student_desc = {}

        for i in LineItemType.objects.filter(anchor=self.program_anchor_cached(parent=True)):
            student_desc[i.text] = """Students who have opted for '%s'""" % i.text

        return student_desc

    def students(self, QObject = False):
        """ Return the useful lists of students for the Extra Costs module. """

        student_lists = {}
        # Get all the line item types for this program.
        for i in LineItemType.objects.filter(anchor=self.program_anchor_cached(parent=True)):
            if QObject:
                student_lists[i.text] = self.getQForUser(Q(accounting_lineitem__li_type = i))
            else:
                student_lists[i.text] = User.objects.filter(accounting_lineitem__li_type = i).distinct()

        return student_lists

    def isCompleted(self):
        return ( Document.objects.filter(user=self.user, anchor=self.program_anchor_cached(parent=True), txn__complete=True).count() > 0 or self.get_invoice().txn.lineitem_set.all().count() > 0 )

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
        
        doc = self.get_invoice()

        if request.method == 'POST':
            costs_db = [ { 'LineItemType': x, 
                           'CostChoice': CostItem(request.POST, prefix="%s_" % x.id) }
                         for x in costs_list ] + \
                         [ x for x in \
                               [ { 'LineItemType': x, 
                                   'CostChoice': MultiCostItem(request.POST, prefix="%s_" % x.id) }
                                 for x in multicosts_list ] \
                               if x['CostChoice'].is_valid() and x['CostChoice'].cleaned_data.has_key('cost') ]

            for i in costs_db:
                if not i['CostChoice'].is_valid():
                    raise ESPError("A non-required boolean is invalid in the Cost module")               

                if i['CostChoice'].cleaned_data['cost']:
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

        else:
            checked_ids = set( [ x.li_type_id for x in doc.txn.lineitem_set.all() ] )
            forms = [ { 'form': CostItem( prefix="%s_" % x.id, initial={'cost': (x.id in checked_ids ) } ),
                        'LineItem': x }
                      for x in costs_list ] + \
                      [ { 'form': MultiCostItem( prefix="%s_" % x.id, initial={'cost': (x.id in checked_ids ), 'count': max(1, doc.txn.lineitem_set.filter(li_type=x).count()) } ),
                          'LineItem': x }
                        for x in multicosts_list ]
                

            return render_to_response(self.baseDir()+'extracosts.html',
                                      request,
                                      (self.program, tl),
                                      { 'forms': forms, 'financial_aid': ESPUser(request.user).hasFinancialAid(prog.anchor), 'select_qty': len(multicosts_list) > 0 })

