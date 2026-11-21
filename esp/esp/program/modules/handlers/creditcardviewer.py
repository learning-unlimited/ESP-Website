
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
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.utils.web       import render_to_response
from esp.accounting.controllers import ProgramAccountingController
from esp.accounting import payment_issues
from esp.accounting.payment_issues import PaymentIssueError
from esp.users.models import ESPUser
from django.contrib import messages
from django.http import HttpResponseRedirect
from decimal import Decimal, InvalidOperation


def _student(user_id):
    try:
        return ESPUser.objects.get(id=int(user_id))
    except (TypeError, ValueError, ESPUser.DoesNotExist):
        raise PaymentIssueError("That student wasn't found.")


def _amount(value):
    try:
        amount = Decimal(value).quantize(Decimal('0.01'))
    except (TypeError, InvalidOperation):
        raise PaymentIssueError('Please enter a valid amount.')
    if not amount.is_finite():
        raise PaymentIssueError('Please enter a valid amount.')
    return amount


class CreditCardViewer(ProgramModuleObj):
    doc = """Lists the credit card payments for the program."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Credit Card View Module",
            "link_title": "View Credit Card Transactions",
            "module_type": "manage",
            "seq": 10000,
            "choosable": 0,
            }

    @main_call
    @needs_admin
    def viewpay(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            self._change_payment_issue(request, prog)
            return HttpResponseRedirect(request.get_full_path())

        pac = ProgramAccountingController(prog)
        student_list = list(pac.all_students())
        payment_table = pac.student_payment_rows(student_list)
        for row in payment_table:
            row['link_amounts'] = ' '.join('%.2f' % amount for amount in payment_issues.linkable_payment_amounts(row))

        #   Also fetch summary information about the payments
        (num_payments, total_payment) = pac.payments_summary(payment_method='card')
        (num_cash, total_cash) = pac.payments_summary(payment_method='cash_check')

        context = {
            'num_cash_payments': num_cash,
            'total_cash_payment': total_cash,
            'program': prog,
            'payment_table': payment_table,
            'num_students': len(student_list),
            'num_payments': num_payments,
            'total_payment': total_payment,
        }
        context.update(payment_issues.payment_issues(prog, payment_table))

        #   Students with open issues go at the top of the table
        payment_table.sort(key=lambda row: not row['issues'])
        context['num_with_issues'] = sum(1 for row in payment_table if row['issues'])

        return render_to_response(self.baseDir() + 'viewpay.html', request, context)

    def _change_payment_issue(self, request, prog):
        """ Carries out a form submitted from the payment issues box (or an
        "Add a payment" form) and queues a message saying what happened. """
        post = request.POST
        try:
            if 'add_payment' in post:
                student = _student(post.get('payment_user'))
                amount = _amount(post.get('amount'))
                (payment, linked) = payment_issues.record_payment(
                    prog, student, amount, post.get('transaction_id'), request.user, post.get('note'),
                    postback_id=post.get('postback') or None)
                messages.success(request, 'Recorded a payment of $%.2f (transaction %s) for %s.' % (
                    payment.amount_dec, payment.transaction_id, student.name()))
                if not linked:
                    messages.warning(request, "It doesn't add up to a set of %s's unpaid items, so none of "
                                     "their items were marked paid by it. It still counts toward their balance." % student.name())
            elif 'resolve' in post and post.get('postback'):
                payment_issues.resolve_postback(prog, post['postback'], request.user, post.get('note'))
                messages.success(request, 'Marked the payment notice #%s resolved.' % post['postback'])
            elif 'resolve' in post and post.get('overpaid_user'):
                student = _student(post['overpaid_user'])
                payment_issues.resolve_overpayment(prog, student, _amount(post.get('overpaid_amount')),
                                                   request.user, post.get('note'))
                messages.success(request, "Marked %s's overpayment resolved." % student.name())
            elif 'reopen' in post and post.get('postback'):
                payment_issues.reopen_postback(prog, post['postback'], request.user)
                messages.success(request, 'Reopened the payment notice #%s.' % post['postback'])
            elif 'reopen' in post and post.get('overpaid_user'):
                student = _student(post['overpaid_user'])
                payment_issues.reopen_overpayment(prog, student, request.user)
                messages.success(request, "Reopened %s's overpayment." % student.name())
            else:
                messages.error(request, "Sorry, that request wasn't understood; nothing was changed.")
        except PaymentIssueError as e:
            messages.error(request, '%s Nothing was changed.' % e)

    def isStep(self):
        return self.program.hasModule('CreditCardModule_Stripe')

    setup_title = "Set up the website for credit card payments (including the 'stripe settings' tag) (you may need to reach out to the websupport team)"
    setup_path = "tags/learn"

    def isCompleted(self):
        module = self.program.getModule('CreditCardModule_Stripe')
        return module is not None and module.check_setup()

    class Meta:
        proxy = True
        app_label = 'modules'
