
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

from esp.users.models import Permission
from django.http import Http404
from esp.web.util.main import render_to_response
from django.core.cache import cache

def branch_find(view_func):
    """
    A decorator to be used on a view.
    The signature of the view its used on is:

    view(request, node, name, section, action, *args **kwargs)

    Where:
       request: A standard HttpRequest object.
       url:     The url, not including any trailing '.html'
       action:  An action that is being performed on this url,
                the standard ones are ['create','edit','read']
    """

    def _new_func(request, url='index', filename=None, *args, **kwargs):

        # Cache which tree node corresponds to this URL
        #cache_key = 'qsdeditor_%s_%s' % (url, filename)
        #cache_key = cache_key.replace(' ', '')
        #retVal = cache.get(cache_key)
        #if retVal is not None:
        #    return view_func(*((request,) + retVal + args), **kwargs)

        # If we didn't find it in the cache, keep looking

        DEFAULT_ACTION = 'read'

        if filename:
            url += '/%s' % filename

        tree_end = url.split('/')

        view_address = tree_end[-1]

        if view_address.strip() == '':
            raise Http404, 'Invalid URL.'

        view_address_pieces = view_address.split('.')

        if len(view_address_pieces) > 1:
            action       = view_address_pieces[-1]
            tree_end[-1] = '.'.join(view_address_pieces[:-1])
        else:
            action       = DEFAULT_ACTION
            tree_end[-1] = view_address_pieces[0]

        url = "/".join(tree_end)

        retVal = (url, action)
        
        #cache.set(cache_key, retVal, 86400)

        return view_func(*((request,) + retVal + args), **kwargs)

    _new_func.__doc__ = view_func.__doc__
    return _new_func


