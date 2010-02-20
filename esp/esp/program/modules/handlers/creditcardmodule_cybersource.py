
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
from esp.program.modules import module_ext
from esp.datatree.models import *
from esp.web.util        import render_to_response
from datetime            import datetime        
from django.db.models.query     import Q
from esp.users.models    import User, ESPUser
from esp.accounting_core.models import LineItemType, EmptyTransactionException, Balance
from esp.accounting_docs.models import Document
from esp.middleware      import ESPError

class CreditCardModule_Cybersource(ProgramModuleObj, module_ext.CreditCardModuleInfo):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Credit Card Payment Module (Cybersource)",
            "link_title": "Credit Card Payment",
            "module_type": "learn",
            "seq": 10000
            }
    
    def extensions(self):
        return []#('creditCardInfo', module_ext.CreditCardModuleInfo)]

    def cost(self, espuser, anchor):
        return '%s.00' % str(self.creditCardInfo.base_cost)

    def isCompleted(self):
        """ Whether the user has paid for this program or its parent program. """
        if ( len(Document.get_completed(self.user, self.program_anchor_cached)) > 0 ):
            return True
        else:
            parent_program = self.program.getParentProgram()
            if parent_program is not None:
                return ( len(Document.get_completed(self.user, parent_program.anchor)) > 0 )
    
    have_paid = isCompleted

    def students(self, QObject = False):
        # this should be fixed...this is the best I can do for now - Axiak
        # I think this is substantially better; it's the same thing, but in one query. - Adam
        #transactions = Transaction.objects.filter(anchor = self.program_anchor_cached())
        #userids = [ x.document_id for x in documents ]
        QObj = Q(document__anchor=self.program_anchor_cached(), document__doctype=3, document__cc_ref__gt='')

        if QObject:
            return {'creditcard': QObj}
        else:
            return {'creditcard':User.objects.filter(QObj).distinct()}



    def studentDesc(self):
        return {'creditcard': """Students who have filled out the credit card form."""}

    @main_call
    @meets_deadline('/Payment')
    @usercheck_usetl
    def startpay_cybersource(self, request, tl, one, two, module, extra, prog):
        if self.have_paid():
            raise ESPError(False), "You've already paid for this program; you can't pay again!"
                    
        return render_to_response(self.baseDir() + 'cardstart.html', request, (prog, tl), {})

    @aux_call
    @meets_deadline('/Payment')
    @usercheck_usetl
    def paynow_cybersource(self, request, tl, one, two, module, extra, prog):
        if self.have_paid():
            raise ESPError(False), "You've already paid for this program; you can't pay again!"
        
        # Force users to pay for non-optional stuffs
        user = ESPUser(request.user)
        
        #   Default line item types
        li_types = self.program.getLineItemTypes(user)

        invoice = Document.get_invoice(user, self.program_anchor_cached(parent=True), li_types, dont_duplicate=True)
        context = {}
        context['module'] = self
        context['one'] = one
        context['two'] = two
        context['tl']  = tl
        context['user'] = user
        context['itemizedcosts'] = invoice.get_items()

        try:
            context['itemizedcosttotal'] = invoice.cost()
        except EmptyTransactionException:
            context['itemizedcosttotal'] = 0
            
        context['financial_aid'] = user.hasFinancialAid(prog.anchor)
        context['invoice'] = invoice
        
        return render_to_response(self.baseDir() + 'cardpay.html', request, (prog, tl), context)
