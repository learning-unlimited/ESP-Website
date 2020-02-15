#!/usr/bin/env python2
#
# Display Auto-Approved Financial Aid Requests
#
# Displays financial aid requests that have been approved or autoapproved,
# sorted by date, so that students can be emailed easily.  Make sure to update
# PROGRAM_ID before running.
#

from script_setup import *

from esp.program.models import FinancialAidRequest

# CONFIGURATION
PROGRAM = "Splash 2014"

# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(program__name=PROGRAM)
tagged_reqs = {}

print "Auto-Approved Requests"

for req in reqs:
    if not req.approved:
        continue
    date = min(x['timestamp'].date() for x in req.financialaidgrant_set.values())
    lst = tagged_reqs.get(date, [])
    lst.append(req)
    tagged_reqs[date] = lst

dates = tagged_reqs.keys()
dates.sort()
for date in dates:
    print "  " + str(date) + ":"
    for req in tagged_reqs[date]:
        print "    %s <%s>" % (req.user.name(), req.user.email)

if reqs.count() == 0:
    print "  No requests"
