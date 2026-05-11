import json
import traceback
from decimal import Decimal
from django.db import transaction
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from esp.accounting.models import CybersourcePostback
from esp.dbmail.models import send_mail
from esp.accounting.controllers import IndividualAccountingController

@csrf_exempt
@transaction.non_atomic_requests
def submit_transaction(request):
    # Before we do anything else, log the raw postback to the database
    pretty_postdata = json.dumps(request.POST, sort_keys=True, indent=4,
                                 separators=(', ', ': '))
    log_record = CybersourcePostback.objects.create(post_data=pretty_postdata)
    transaction.commit()
    try:
        return _submit_transaction(request, log_record)
    except Exception:
        subject = '[ESP CC] Failed to process Cybersource postback'
        log_uri = request.build_absolute_uri(
            reverse('admin:accounting_cybersourcepostback_change', args=(log_record.id,)))
        message = 'The following Cybersource postback could not be processed. Please ' + \
                  'reconcile it by hand:\n\n    %s\n\n%s' % (log_uri, traceback.format_exc())
        from_addr = settings.SERVER_EMAIL
        recipients = [settings.DEFAULT_EMAIL_ADDRESSES['treasury']]
        send_mail(subject, message, from_addr, recipients)
        raise

@transaction.atomic
def _submit_transaction(request, log_record):
    decision = request.POST['decision']
    if decision == "ACCEPT":
        # Handle payment
        identifier = request.POST['req_merchant_defined_data1']
        amount_paid = Decimal(request.POST['req_amount'])
        transaction_id = request.POST['transaction_id']

        payment = IndividualAccountingController.record_payment_from_identifier(
            identifier, amount_paid, transaction_id)

        # Link payment to log record
        log_record.transfer = payment
        log_record.save()

        return _redirect_from_identifier(identifier, "success")
    elif decision == "DECLINE":
        identifier = request.POST['req_merchant_defined_data1']
        return _redirect_from_identifier(identifier, "declined")
    else:
        raise NotImplementedError("Can't handle decision: %s" % decision)

def _redirect_from_identifier(identifier, result):
    program = IndividualAccountingController.program_from_identifier(identifier)
    destination = "/learn/%s/cybersource?result=%s" % (program.getUrlBase(), result)
    return HttpResponseRedirect(destination)
