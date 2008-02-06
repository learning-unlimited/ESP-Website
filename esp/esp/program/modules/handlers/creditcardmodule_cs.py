
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
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.money.models    import PaymentType, Transaction
from datetime            import datetime        
from esp.db.models       import Q
from esp.users.models    import User
from esp.accounting_core.models import LineItem, LineItemType, Balance, Transaction
from esp.accounting_docs.models import Document

class CreditCardModule_CS(ProgramModuleObj):
    def cost(self, espuser, anchor):
        return Document.get_invoice(espuser, self.program.anchor).txn.get_balance()

    def isCompleted(self):
        return Document.get_invoice(self.user, self.program.anchor).txn.complete

    def students(self, QObject = False):
        if QObject:
            return {'creditcard': Q()}
        else:
            return {'creditcard': []}

    def studentDesc(self):
        return {'creditcard': """Students who have paid using the new credit card module."""}
     
    @meets_deadline('/Payment')
    @usercheck_usetl
    def startpay(self, request, tl, one, two, module, extra, prog):
        # Force users to pay for non-optional stuffs
        for i in LineItemType.objects.filter(anchor=prog.anchor, optional=False):
            RegisterLineItem(request.user, i)

        context = {}
        context['module'] = self
        context['one'] = one
        context['two'] = two
        context['tl']  = tl
        context['itemizedcosts'] = LineItem.purchased(prog.anchor, request.user, filter_already_paid=False)
        context['itemizedcosttotal'] = LineItem.purchasedTotalCost(prog.anchor, request.user)
        context['financial_aid'] = LineItem.student_has_financial_aid(request.user, prog.anchor)
        return render_to_response(self.baseDir() + 'cardstart.html', request, (prog, tl), context)

    @usercheck_usetl
    def paynow(self, request, tl, one, two, module, extra, prog):
        # Force users to pay for non-optional stuffs.  Once more, just in case.
        for i in LineItemType.objects.filter(anchor=prog.anchor, optional=False):
            RegisterLineItem(request.user, i)

        context = {'module': self}
        paymenttype = PaymentType.objects.get(description__icontains = 'credit card')
        payment = Transaction()
        payment.anchor = self.program_anchor_cached()
        payment.executed = False # have not verified yet...
        payment.fbo = self.user
        payment.payer = self.user
        payment.payment_type = paymenttype
        payment.line_item = 'Credit-card payment for "%s"' % self.program.niceName()
        payment.amount = LineItem.purchasedTotalCost(prog.anchor, request.user)
        payment.save()
        
        self.payment = payment

        yearnow = datetime.now().year
        context['years'] = zip(['%02d' % x for x in
                                range(yearnow-2000,yearnow+20-2000)],
                               range(yearnow, yearnow+20))
        context['module'] = self

        context['itemizedcosts'] = list(LineItem.purchased(prog.anchor, request.user)) # Force this to be evaluated now, not after we've marked things as paid
        context['itemizedcosttotal'] = LineItem.purchasedTotalCost(prog.anchor, request.user)
        context['financial_aid'] = LineItem.student_has_financial_aid(request.user, prog.anchor)

        PayForLineItems(request.user, prog.anchor, payment)

        return render_to_response(self.baseDir() + 'cardpay.html', request, (prog, tl), context)
