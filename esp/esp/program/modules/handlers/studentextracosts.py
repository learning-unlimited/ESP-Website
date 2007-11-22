
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.datatree.models import GetNode, DataTree
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.middleware      import ESPError
from esp.users.models    import ESPUser, UserBit, User
from esp.db.models       import Q
from django.template.loader import get_template
from esp.program.models  import JunctionStudentApp
from django              import newforms as forms
from django.contrib.auth.models import User

from esp.money.models import LineItemType, LineItem, RegisterLineItem, UnRegisterLineItem

class CostItem(forms.Form):
    cost = forms.BooleanField(required=False, label='')

# pick extra items to buy for each program
class StudentExtraCosts(ProgramModuleObj):


    def studentDesc(self):
        """ Return a description for each line item type that students can be filtered by. """
        student_desc = {}

        for i in LineItemType.objects.filter(anchor=self.program_anchor_cached()):
            student_desc[i.label] = """Students who have opted for '%s'""" % i.label

        return student_desc

    def students(self, QObject = False):
        """ Return the useful lists of students for the Extra Costs module. """

        student_lists = {}
        # Get all the line item types for this program.
        for i in LineItemType.objects.filter(anchor=self.program_anchor_cached()):
            if QObject:
                student_lists[i.label] = self.getQForUser(Q(lineitem__type = i))
            else:
                student_lists[i.label] = User.objects.filter(lineitem__type = i).distinct()

        return student_lists

    def isCompleted(self):
        return LineItem.purchased(self.program_anchor_cached(), self.user).count() > 0

    @needs_student
    @meets_deadline('/ExtraCosts')
    def extracosts(self,request, tl, one, two, module, extra, prog):
        """
        Query the user for any extra items they may wish to purchase for this program

        This module should ultimately deal with things like optional lab fees, etc.
        Right now it doesn't.
        """
        # Force users to pay for non-optional stuffs
        for i in LineItemType.objects.filter(anchor=prog.anchor, optional=False):
            RegisterLineItem(request.user, i)
        
        #costs_list = set(LineItemType.forAnchor(prog.anchor).filter(optional=True).filter(lineitem__transaction__isnull=False, lineitem__user=request.user)) | set([x for x in LineItemType.forAnchor(prog.anchor).filter(optional=True) if x.lineitem_set.count() == 0])
        costs_list = LineItemType.forAnchor(prog.anchor).filter(optional=True)

        if request.method == 'POST':
            costs_db = [ { 'LineItemType': x, 
                           'CostChoice': CostItem(request.POST, prefix="%s_" % x.id) }
                         for x in costs_list ]

            for i in costs_db:
                if not i['CostChoice'].is_valid():
                    raise ESPError("A non-required boolean is invalid in the Cost module")               

                if i['CostChoice'].clean_data['cost']:
                    RegisterLineItem(request.user, i['LineItemType'])
                elif i['LineItemType'].optional:
                    UnRegisterLineItem(request.user, i['LineItemType'])

            return self.goToCore(tl)

        else:
            checked_ids = set( [ x['id'] for x in LineItem.purchasedTypes(prog.anchor, request.user).values('id') ] )
            forms = [ { 'form': CostItem( prefix="%s_" % x.id, initial={'cost': (x.id in checked_ids ) } ),
                        'LineItem': x,
                        'IsPaidFor': x.lineitem_set.filter(transaction__isnull=False, user=request.user) }
                      for x in costs_list ]

            return render_to_response(self.baseDir()+'extracosts.html',
                                      request,
                                      (self.program, tl),
                                      { 'forms': forms, 'financial_aid': LineItem.student_has_financial_aid(request.user, prog.anchor) })

