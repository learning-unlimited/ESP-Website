#!/usr/bin/env python2
#
# Approve Financial Aid Requests
# 
# Approves not-yet-approved requests where both answers are non-blank/None/whitespace
# and prints the email address of these users to the screen. Make sure to configure
# PROGRAM_ID and (in dollars) below.
#

from script_setup import *

from esp.program.models import FinancialAidRequest
from esp.accounting.models import FinancialAidGrant

import re


# CONFIGURATION
PROGRAM = "Splash 2014"


# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(done = False, program__name=PROGRAM).exclude(household_income = None, extra_explaination = None)

print "New Approvals:"
approved_any = False

for req in reqs:
    if (req.household_income is None or re.match(r'^(\s)*$', req.household_income)) and \
        (req.extra_explaination is None or re.match(r'(\s)*$', req.extra_explaination)):
        continue

    if req.financialaidgrant_set.all().count() != 0 : continue

    print req.user.email
    try:
        f = FinancialAidGrant(request = req, percent = 100)
        f.save()
        req.done = True
        req.save()
    except:
        print "Error on user %s" % req.user.id
    approved_any = True

if not approved_any:
    print "None"  # no new (valid) requests to approve
