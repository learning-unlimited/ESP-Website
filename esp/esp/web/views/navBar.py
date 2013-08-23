
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
from esp.web.models import NavBarEntry, NavBarCategory
from esp.users.models import AnonymousUser, ESPUser
from django.http import HttpResponseRedirect, Http404, HttpResponse
from esp.dblog.models import error
from esp.middleware.esperrormiddleware import ESPError

from esp.program.models import Program
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models.query import Q

def nav_category(section=''):
    """ A function to guess the appropriate navigation category when one
        is not provided in the context. """
        
    #   See if there's a category with the provided section name.
    categories = NavBarCategory.objects.filter(name=section)
    if categories.count() > 0:
        return categories[0]
    
    #   If all else fails, make something up.
    return NavBarCategory.default()

def makeNavBar(section='', category=None):
    if not category:
        category = nav_category(section)

    navbars = list(category.get_navbars().order_by('sort_rank'))
    navbar_context = [{'entry': x} for x in navbars]
    context = { 'entries': navbar_context,
                'section': section }
    return context



