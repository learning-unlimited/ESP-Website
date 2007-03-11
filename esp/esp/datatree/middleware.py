
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


class DataTreeLockMiddleware(object):
    """
       This middleware checks to see if the tree is in a HARD LOCK.
       If it is, it will error out before people see strange things
       happening to the web site.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):       
        from esp.datatree.models import DataTree
        from django.shortcuts    import render_to_response

        if DataTree.locked() > 1:
            " The tree is HARD LOCKED. "
            error = 'Sorry, the web site is undergoing scheduled maintenance.' +\
                    '<br />\n' +\
                    'It should be back up in approximately 30 seconds. Please check back at that time.'

            context = {'request': request,'error': error}

            response = render_to_response('error.html', context)

            response['Refresh'] = '20'

            return response

        return None
