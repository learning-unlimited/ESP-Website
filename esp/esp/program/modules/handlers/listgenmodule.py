
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.program.manipulators import SATPrepInfoManipulator
from django.core.cache import cache
from esp.program.models import SATPrepRegInfo
from esp.users.models   import ESPUser, User
from django.db.models.query      import Q
from django.template.defaultfilters import urlencode
from django.template import Context, Template
from esp.miniblog.models import Entry


class ListGenModule(ProgramModuleObj):
    """ While far from complete, this will allow you to just generate a simple list of users matching a criteria (criteria very similar to the communications panel)."""
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Generate List of Users",
            "module_type": "manage",
            "seq": 500
            }

    @main_call
    @needs_admin
    def selectList(self, request, tl, one, two, module, extra, prog):
        """ Select the type of list that is requested. """
        from esp.users.views     import get_user_list
        from esp.users.models    import User
        from esp.users.models import PersistentQueryFilter

        if not request.GET.has_key('filterid'):
            filterObj, found = get_user_list(request, self.program.getLists(True))
        else:
            filterid  = request.GET['filterid']
            filterObj = PersistentQueryFilter.getFilterFromID(filterid, User)
            found     = True
        if not found:
            return filterObj

        if not 'type' in request.GET:
            return render_to_response(self.baseDir()+'options.html', request, (prog, tl), {'filterid': filterObj.id})

        strtype = request.GET['type']

        users = [ ESPUser(user) for user in User.objects.filter(filterObj.get_Q()).filter(is_active=True).distinct() ]

        users.sort()
        
        return render_to_response(self.baseDir()+('list_%s.html'%strtype), request, (prog, tl), {'users': users, 'listdesc': filterObj.useful_name})
                                                                                                 

