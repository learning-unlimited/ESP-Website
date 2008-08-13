
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
from esp.money.models import Transaction
from esp.web.util import render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django import oldforms

def create_reimbursement(request):
    manipulator = Transaction.AddManipulator()

    if request.POST:
        pyPOST = request.POST.copy()

        # We allow a user to leave 'fbo' blank;
        # if they do this, we clone 'payer' into it
        if pyPOST['fbo'] == '':
            pyPOST['fbo'] = pyPOST['payer']                             

        errors = manipulator.get_validation_errors(pyPOST)

        if not errors:
            # The data's good; we can save it
            manipulator.do_html2python(pyPOST)

            # Reimbursements are Transactions that haven't been executed yet.
            # We could theoretically have a bit that gives a user
            # immediate-accept of reimbursements; not sure that we want this
            if pyPOST.has_key('executed') and pyPOST['executed'] == True:
                pyPOST['executed'] == False

            # Save the data from the Web form
            reimbursement = manipulator.save(pyPOST)

            # Hack to make browsers happy to not re-post data
            return HttpResponseRedirect('thanks.html')

    else:
        errors = pyPOST = {}

    form = oldforms.FormWrapper(manipulator, pyPOST, errors)
    return render_to_response('money/reimbursement_request.html', { 'form': form } )

