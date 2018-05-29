
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from datetime import datetime

from django.db.models.query import Q

from esp.miniblog.models import Entry, AnnouncementLink
from esp.users.models import ESPUser, AnonymousESPUser

from argcache import cache_function

# Function for previewing announcements  - Michael P
# Generates the block structure used by battle screens

def preview_miniblog(request, section = None):
    """this function will return the last n miniblog entries from preview_miniblog """
    # last update: Axiak

    if request.user != None:
        curUser = request.user
    else:
        curUser = AnonymousESPUser()

    return curUser.getMiniBlogEntries()

@cache_function
def get_visible_announcements(user, limit, tl):
    models_to_search = [Entry, AnnouncementLink]
    results = []
    grand_total = 0
    overflowed = False
    for model in models_to_search:
        result = model.objects.order_by('-timestamp').filter(Q(highlight_expire__gte = datetime.now()) | Q(highlight_expire__isnull = True)).filter(Q(highlight_begin__lte = datetime.now()) | Q(highlight_begin__isnull = True))

        if tl:
            result = result.filter(section=tl)

        if limit:
            overflowed = ((len(result) - limit) > 0)
            total = len(result)
            result = result[:limit]
        else:
            overflowed = False
            total = len(result)

        results += result
        grand_total += total

    return {'announcementList': results,
              'overflowed':       overflowed,
              'total':            grand_total}
get_visible_announcements.depend_on_model(Entry)
get_visible_announcements.depend_on_model(AnnouncementLink)
