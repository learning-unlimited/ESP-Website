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

from esp.program.models import FinancialAidRequest
from datetime import datetime
import re


# CONFIGURATION
PROGRAM_ID = 50708  # Splash! 2012
#  the id of the program in the datatree


# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(program__anchor__id=PROGRAM_ID).exclude(approved=None).order_by('-approved')

print "Auto-Approved Requests"
if reqs.count() == 0:
    print "  No requests"

last_date = None

for req in reqs:
    if last_date != req.approved.date():
        last_date = req.approved.date()
        print last_date.strftime('%a %d %b:')

    print "  " + req.user.email
