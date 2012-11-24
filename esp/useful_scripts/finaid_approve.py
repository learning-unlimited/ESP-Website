#
# Approve Financial Aid Requests
# 
# Approves not-yet-approved requests where both answers are non-blank/None/whitespace
# and prints the email address of these users to the screen. Make sure to configure
# PROGRAM_ID and PROGRAM_COST (in dollars) below.
#
# This script should be run from the manage.py shell
#

from esp.program.models import FinancialAidRequest
from datetime import datetime
import re


# CONFIGURATION
PROGRAM_ID = 50708  # Splash! 2012
#  the id of the program in the datatree
PROGRAM_COST = 40


# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(program__anchor__id=PROGRAM_ID, approved=None)

print "New Approvals:"
approved_any = False

for req in reqs:
    if (req.household_income is None or re.match(r'^(\s)*$', req.household_income)) and \
        (req.extra_explaination is None or re.match(r'(\s)*$', req.extra_explaination)):

       continue
    
    print req.user.email
    req.approved = datetime.now()
    req.amount_received = PROGRAM_COST
    req.amount_needed = 0
    req.save()
    approved_any = True

if not approved_any:
    print "None"  # no new (valid) requests to approve
