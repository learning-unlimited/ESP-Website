#!/usr/bin/env python2
#
# Display Auto-Approved Financial Aid Requests
# 
# Displays financial aid requests where the student has reported that they
# receive free or reduced-price lunch so that these students can be
# contacted after the initial email batch has been sent. Sorted by date,
# descending. Make sure to update PROGRAM_ID before running.
#
# This script should be run from the manage.py shell
#

from script_setup import *

from esp.program.models import FinancialAidRequest

# CONFIGURATION
PROGRAM = "Splash! 2013"

# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(program__name=PROGRAM).exclude(done=False)

print "Auto-Approved Requests"
if reqs.count() == 0:
    print "  No requests"

last_date = None

print ", ".join([ req.user.email for req in reqs ])


