#!/usr/bin/env python2
#
# Approve Financial Aid Requests
# 
# Approves not-yet-approved requests where both answers are non-blank/None/whitespace
# and prints the email address of these users to the screen. Make sure to configure
# PROGRAM_ID below.
#

from script_setup import *

from esp.program.models import FinancialAidRequest
from esp.accounting.models import FinancialAidGrant

import re


# CONFIGURATION
PROGRAM = "Splash 2014"


# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(program__name=PROGRAM)

print "New Approvals:"
approved_any = False

def is_blank(x):
    return x is None or re.match(r'^(\s)*$', x)

for req in reqs:
    if is_blank(req.household_income) and is_blank(req.extra_explaination):
        continue

    if req.approved:
        continue

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
