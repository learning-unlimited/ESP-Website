
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
  Email: web-team@lists.learningu.org
"""
from django.http import HttpResponse
from django.utils import simplejson
from django.db.models.query import Q
from esp.datatree.models import *

class JsonResponse(HttpResponse):
    def __init__(self, obj):
        self.original_obj = obj
        HttpResponse.__init__(self, self.serialize())
#self["Content-Type"] = "application/json"
        self["Content-Type"] = "text/plain"

    def serialize(self):
        return(simplejson.dumps(self.original_obj))

def teacher_lookup(request, limit=10):
     # FIXME: REQUIRE PERMISSIONS!
    
    queryset = ESPUser.objects.filter(group__name="Teacher")


    # Search for teachers with names that start with search string
    startswith = request.GET['q']
    parts = startswith.split(', ')
    Q_name = Q(user__last_name__istartswith=parts[0])
    if len(parts) > 1:
	Q_name = Q_name & Q(user__first_name__istartswith=parts[1])

    # Isolate user objects
    queryset = queryset.filter(Q_name)[:(limit*10)]
    users = [ub.user for ub in queryset]
    user_dict = {}
    for user in users:
    	user_dict[user.id] = user
    users = user_dict.values()

    # Construct combo-box items
    obj_list = [[user.last_name + ', ' + user.first_name, user.id] for user in users]

    # Operation Complete!
    return JsonResponse(obj_list)

