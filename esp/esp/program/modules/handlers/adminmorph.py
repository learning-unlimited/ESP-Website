
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
from django.http     import HttpResponseRedirect
from esp.users.views import search_for_user
from esp.db.models   import Q
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite, main_call, aux_call
from esp.program.modules.handlers.programprintables import ProgramPrintables
from esp.web.util import render_to_response
from django.contrib.auth.models import User

class AdminMorph(ProgramModuleObj):
    doc = """ User morphing allows the program director to morph into a constituent of their program. """
    def module_properties(self):
        return {
            "link_title": "Morph into User",
            "module_type": "manage",
            "seq": 34
            }

    @main_call
    @needs_admin
    def admin_morph(self, request, tl, one, two, module, extra, prog):
        """ This function will allow someone to morph into a user for testing purposes. """

        #   If there's no 'extra' component to the URL, return the options page.
        if extra is None or extra == '':
            context = {'module': self}
            return render_to_response(self.baseDir()+'options.html', request, (prog, tl), context)

        #   Default query is to get program participants
        query = self.program.students_union(True) | self.program.teachers_union(True)
        
        #   List all of the useful queries we can think of.  If we had some autosave (pickle type)
        #   feature, that could be really cool.
        saved_queries = {   'student': self.program.students_union(True),
                            'teacher': self.program.teachers_union(True),
                            'program': self.program.students_union(True) | self.program.teachers_union(True),
                            'all': Q()
                        }
                        
        if extra in saved_queries:
            query = saved_queries[extra]
        
        user, found = search_for_user(request, User.objects.filter(query))

        if not found:
            return user

        self.user.switch_to_user(request,
                                 user,
                                 self.getCoreURL(tl),
                                 'Managing %s' % self.program.niceName(),
                                 False)

        return HttpResponseRedirect('/')

