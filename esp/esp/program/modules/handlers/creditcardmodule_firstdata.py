
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
from esp.program.modules import module_ext
from esp.datatree.models import *
from esp.web.util        import render_to_response
from datetime            import datetime        
from django.db.models.query     import Q
from django.http         import HttpResponseRedirect
from django.core.mail import send_mail
from esp.users.models    import User, ESPUser
from esp.accounting_core.models import LineItemType, EmptyTransactionException, Balance, CompletedTransactionException
from esp.accounting_docs.models import Document
from esp.middleware      import ESPError
from esp.settings import INSTITUTION_NAME, DEFAULT_EMAIL_ADDRESSES

class CreditCardModule_FirstData(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Credit Card Payment Module (First Data)",
            "link_title": "Credit Card Payment",
            "module_type": "learn",
            "seq": 10000,
            "main_call": "payonline",
            }

    def isCompleted(self):
        """ Whether the user has paid for this program or its parent program. """
        if ( len(Document.get_completed(self.user, self.program_anchor_cached())) > 0 ):
            return True
        else:
            parent_program = self.program.getParentProgram()
            if parent_program is not None:
                return ( len(Document.get_completed(self.user, parent_program.anchor)) > 0 )
        return False
    
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

    def payment_success(self, request, tl, one, two, module, extra, prog):
        """ Receive payment from First Data Global Gateway """

        if request.POST.get('status', '') != 'APPROVED':
            return self.payment_failure(request, tl, one, two, module, extra, prog)

        try:
            from decimal import Decimal
            post_locator = request.POST.get('invoice_number', '')
            post_amount = Decimal(request.POST.get('total', '0.0'))
            post_id = request.POST.get('refnumber', '')       
            document = Document.receive_creditcard(request.user, post_locator, post_amount, post_id)
        except CompletedTransactionException:
            from django.conf import settings
            invoice = Document.get_by_locator(post_locator)
            # Look for duplicate payment by checking old receipts for different cc_ref.
            cc_receipts = invoice.docs_next.filter(cc_ref__isnull=False).exclude(cc_ref=post_id)
            # Prepare to send e-mail notification of duplicate postback.
            recipient_list = [contact[1] for contact in settings.ADMINS]
            refs = 'Cybersource request ID: %s' % post_id
            if cc_receipts:
                subject = 'DUPLICATE PAYMENT'
                refs += '\n\nPrevious payments\' Cybersource IDs: ' + ( u', '.join([x.cc_ref for x in cc_receipts]) )
            else:
                subject = 'Duplicate Postback'
            # Send mail!
            send_mail('[ ESP CC ] ' + subject + ' for #' + post_locator + ' by ' + invoice.user.first_name + ' ' + invoice.user.last_name, \
                  """%s Notification\n--------------------------------- \n\nDocument: %s\n\n%s\n\nUser: %s %s (%s)\n\nCardholder: %s\n\nProgram anchor: %s\n\nRequest: %s\n\n""" % \
                  (subject, invoice.locator, refs, invoice.user.first_name, invoice.user.last_name, invoice.user.id, request.POST.get('bname', '--'), invoice.anchor.get_uri(), request) , \
                  settings.SERVER_EMAIL, recipient_list, True)
            # Get the document that would've been created instead
            document = invoice.docs_next.all()[0]
        except:
            raise
            # raise ESPError(), "Your credit card transaction was successful, but a server error occurred while logging it.  The transaction has not been lost (please do not try to pay again!); this just means that the green Credit Card checkbox on the registration page may not be checked off.  Please <a href=\"mailto:%s\">e-mail us</a> and ask us to correct this manually.  We apologize for the inconvenience." % DEFAULT_EMAIL_ADDRESSES['support']

        one = document.anchor.parent.name
        two = document.anchor.name

        context = {}
        context['postdata'] = request.POST.copy()
        context['support_email'] = DEFAULT_EMAIL_ADDRESSES['support']
        context['prog'] = prog

        #   Don't redirect to receipt just yet, in case they haven't finished all steps of registration
        #   return HttpResponseRedirect("http://%s/learn/%s/%s/confirmreg" % (request.META['HTTP_HOST'], one, two))
        return render_to_response(self.baseDir() + 'success.html', request, (prog, tl), context)
        

    def payment_failure(self, request, tl, one, two, module, extra, prog):
        context = {}
        context['postdata'] = request.POST.copy()
        context['prog'] = prog
        context['support_email'] = DEFAULT_EMAIL_ADDRESSES['support']

    @aux_call
    @meets_deadline('/Payment')
    @usercheck_usetl
    def payonline(self, request, tl, one, two, module, extra, prog):
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
        context['program'] = self.program
        context['hostname'] = request.META['HTTP_HOST']
        context['institution'] = INSTITUTION_NAME
        context['storename'] = '1909968401' # Learning Unlimited, Inc.

        try:
            context['itemizedcosttotal'] = invoice.cost()
        except EmptyTransactionException:
            context['itemizedcosttotal'] = 0
            
        context['financial_aid'] = user.hasFinancialAid(prog.anchor)
        context['invoice'] = invoice
        
        return render_to_response(self.baseDir() + 'cardpay.html', request, (prog, tl), context)
