#
# Approve Financial Aid Requests
# Criteria: both answers non-blank/None/whitespace
#
# This script should be run from the manage.py shell
#

from esp.program.models import FinancialAidRequest
from datetime import datetime
import re


# CONFIGURATION
PROGRAM_ID = 50708
#  the id of the program in the datatree


# ITERATE & APPROVE REQUESTS
reqs = FinancialAidRequest.objects.filter(program__anchor__id=PROGRAM_ID, approved=None)

for req in reqs:
    if (req.household_income is None or re.match(r'^(\s)*$', req.household_income)) and \
        (req.extra_explaination is None or re.match(r'(\s)*$', req.extra_explaination)):

       continue
    
    req.approved = datetime.now()
    req.save()
