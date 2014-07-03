#!/usr/bin/env python2
#
# Approve Financial Aid Requests
# 
# Approves not-yet-approved requests where both answers are non-blank/None/whitespace
# and prints the email address of these users to the screen. Make sure to configure
# PROGRAM_ID and PROGRAM_COST (in dollars) below.
#

from script_setup import *

from esp.program.models import FinancialAidRequest
from esp.accounting.models import FinancialAidGrant


# CONFIGURATION
PROGRAM = "Splash! 2013"
PROGRAM_COST = 40


# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(done = False, program__name=PROGRAM).exclude(household_income = None, extra_explaination = None)

print reqs.count()

print "New Approvals:"
approved_any = False

emails = []
errors = []

for req in reqs:
#    if (req.household_income is None or re.match(r'^(\s)*$', req.household_income)) and \
#        (req.extra_explaination is None or re.match(r'(\s)*$', req.extra_explaination)):

#    if req.household_income is None and req.extra_explaination is None:
#       continue

    print req.user

    if req.financialaidgrant_set.all().count() != 0 : continue

    e = req.user.email
    print e
    emails.append(e)
    try:
        f = FinancialAidGrant(request = req, percent = 100)
        f.save()
        req.done = True
        req.save()
    except:
        errors.append(req.user)
    approved_any = True

if not approved_any:
    print "None"  # no new (valid) requests to approve
