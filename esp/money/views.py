from esp.money.models import Transaction
from esp.web.data import render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django import forms

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

    form = forms.FormWrapper(manipulator, pyPOST, errors)
    return render_to_response('money/reimbursement_request.html', { 'form': form } )
