'''Things that will be useful to have in shell_plus, which it will auto-import.'''

from django.db.models import F, Q, Count, Avg, Min, Max, Sum

import datetime

from esp.utils.query_utils import nest_Q
from esp.program.modules.models import install
