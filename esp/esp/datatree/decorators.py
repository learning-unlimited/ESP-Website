
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

from esp.users.models    import GetNodeOrNoBits, PermissionDenied
from esp.datatree.models import DataTree, GetNode
from django.http import Http404
from esp.web.util.main import render_to_response
from django.core.cache import cache

# Where to start our tree search.

from esp.urls import section_redirect_keys
   
subsection_map = {
    'programs': '',
    }    
    
def branch_find(view_func):
    """
    A decorator to be used on a view.
    The signature of the view its used on is:

    view(request, node, name, section, action, *args **kwargs)

    Where:
       request: A standard HttpRequest object.
       node:    A DataTree node corresponding to this url.
       name:    The name of the node, e.g. 'learn:index'.
       section: A section, e.g. 'learn', or 'teach'.
       action:  An action that is being performed on this url,
                the standard ones are ['create','edit','read']
    """

    def _new_func(request, url='index', subsection=None, filename=None, *args, **kwargs):

        # Cache which tree node corresponds to this URL
        cache_key = 'qsdeditor_%s_%s_%s_%s' % (request.user.id,
                                               url, subsection, filename)
        cache_key = cache_key.replace(' ', '')
        retVal = cache.get(cache_key)
        if retVal is not None:
            return view_func(*((request,) + retVal + args), **kwargs)

        # If we didn't find it in the cache, keep looking

        # function "constants"
        READ_VERB = GetNode('V/Flags/Public')
        DEFAULT_ACTION = 'read'

        if filename:
            url += '/%s' % filename

        # the root of the datatree
        section = section_redirect_keys[subsection]
        
        #   Rewrite 'subsection' if we want to.
        if subsection_map.has_key(subsection):
            subsection = subsection_map[subsection]
        tree_root = 'Q/' + section

        tree_end = url.split('/')

        view_address = tree_end.pop()

        if view_address.strip() == '':
            raise Http404, 'Invalid URL.'

        tree_node_uri = tree_root + '/' + '/'.join(tree_end)


        view_address_pieces = view_address.split('.')

        if len(view_address_pieces) > 1:
            action       = view_address_pieces[-1]
            view_address = '.'.join(view_address_pieces[:-1])
        else:
            action       = DEFAULT_ACTION
            view_address = view_address_pieces[0]


        try:
            # attempt to get the node
            branch = GetNodeOrNoBits(tree_node_uri,
                                     request.user,
                                     READ_VERB,
                                    #only create if we are planning on writing.
                                     action in ('create','edit',)
                                     )
        except PermissionDenied:
            raise Http404, "No such site, no bits to create it: '%s'" % \
                         tree_node_uri
        except DataTree.NoSuchNodeException, e:
            edit_link = request.path[:-5]+'.edit.html'
            branch = e.anchor
            return render_to_response('qsd/nopage_create.html',
                                      request,
                                      (branch, section),
                                      {'edit_link': edit_link})

        if subsection:
            view_address = "%s:%s" % (subsection, view_address)

        retVal = (branch, view_address, subsection, action)

        if request.user.id is None:
            cache.set(cache_key, retVal, 86400)
        else:
            cache.set(cache_key, retVal, 3600)

        return view_func(*((request,) + retVal + args), **kwargs)

    _new_func.__doc__ = view_func.__doc__
    return _new_func


