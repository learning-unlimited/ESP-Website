
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
from esp.datatree.models import DataTree
from django.http import Http404
from esp.web.util.main import render_to_response

# Where to start our tree search.

section_redirect_keys = {
    'teach':   'Programs',
    'manage':  'Programs',
    'onsite':  'Programs',    
    'learn':   'Programs',
    'program': 'Programs',
    'help':    'ESP/Committees',
    None:      'Web',
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

    def _new_func(request, url, subsection=None, filename=None, *args, **kwargs):

        # function "constants"
        READ_VERB = request.get_node('V/Flags/Public')
        DEFAULT_ACTION = 'read'

        if filename:
            url += '/%s' % filename

        # the root of the datatree
        section = section_redirect_keys[subsection]
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
        except DataTree.NoSuchNodeException:
            edit_link = request.path[:-5]+'.edit.html'
            branch = DataTree.get_lowest_parent(tree_node_uri)
            return render_to_response('qsd/nopage_create.html',
                                      request,
                                      (branch, section),
                                      {'edit_link': edit_link})

        if subsection:
            view_address = "%s:%s" % (subsection, view_address)

        return view_func(request, branch, view_address,
                         subsection, action, *args,**kwargs)

    _new_func.__doc__ = view_func.__doc__
    return _new_func
