#!/usr/bin/env python2
#
# Approve Financial Aid Requests
#
# Approves not-yet-approved requests where both answers are non-blank/None/whitespace
# and prints the email address of these users to the screen.

from __future__ import print_function
from script_setup import *

from esp.program.models import FinancialAidRequest
from esp.accounting.models import FinancialAidGrant

import re
import sys

if len(sys.argv) < 2:
    print("Usage: {} <program name>".format(sys.argv[0]), file=sys.stderr)
    print("<program name> can be e.g. 'Splash 2016'")
    exit(1)

# if you call the script with multiple arguments you probably just forgot to
# quote it
PROGRAM = ' '.join(sys.argv[1:])

# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(program__name=PROGRAM)

# computing len will use the same query we're probably going to use later and
# populate the query set cache (whereas if we used .exists() or .count(), they
# wouldn't, and the later iteration would hit the database again)
if len(reqs) == 0:
    print("No requests found for program name '%s'!" % PROGRAM)
    exit(1)

print("New Approvals:")
approved_any = False

def is_blank(x):
    return x is None or re.match(r'^(\s)*$', x)

for req in reqs:
    if is_blank(req.household_income) and is_blank(req.extra_explaination):
        continue

    if req.approved:
        continue

    print(req.user.email)
    try:
        f = FinancialAidGrant(request = req, percent = 100)
        f.save()
        req.done = True
        req.save()
    except:
        print("Error on user %s" % req.user.id)
    approved_any = True

if not approved_any:
    print("None") # no new (valid) requests to approve
