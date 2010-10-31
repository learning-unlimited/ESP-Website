
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
from esp.money.models import Transaction
from esp.web.util import render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.forms import ModelForm

class TransactionForm(ModelForm):
    class Meta:
        model = Transaction

def create_reimbursement(request):
    if request.POST:
        pyPOST = request.POST.copy()

        # We allow a user to leave 'fbo' blank;
        # if they do this, we clone 'payer' into it
        if pyPOST['fbo'] == '':
            pyPOST['fbo'] = pyPOST['payer']                             

        f = TransactionForm(pyPOST)

        if f.is_valid():
            # Reimbursements are Transactions that haven't been executed yet.
            # We could theoretically have a bit that gives a user
            # immediate-accept of reimbursements; not sure that we want this
            if f.cleaned_data.has_key('executed') and f.cleaned_data['executed'] == True:
                f.cleaned_data['executed'] == False

            # Save the data from the Web form
            reimbursement = f.save()

            # Hack to make browsers happy to not re-post data
            return HttpResponseRedirect('thanks.html')

    else:
        f = TransactionForm()

    return render_to_response('money/reimbursement_request.html', { 'form': f } )

