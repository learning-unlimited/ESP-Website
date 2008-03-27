
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline, CoreModule
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.miniblog.models import Entry
from esp.datatree.models import GetNode

class TeacherRegCore(ProgramModuleObj, CoreModule):
    
    @meets_deadline("/MainPage")
    @needs_teacher
    def teacherreg(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher reg page """
        context = {}
        modules = self.program.getModules(self.user, 'teach')

        context['completedAll'] = True
        for module in modules:
            if not module.isCompleted() and module.required:
                context['completedAll'] = False
                
            context = module.prepare(context)

        context['modules'] = modules
        context['one'] = one
        context['two'] = two

        context['progposts'] = Entry.find_posts_by_perms(self.user,GetNode('V/Subscribe'),
                                                         self.program_anchor_cached().tree_create(['Announcements', 'Teachers']))
        return render_to_response(self.baseDir()+'mainpage.html', request, (prog, tl), context)

    def isStep(self):
        return False
    
    def getNavBars(self):
        if super(TeacherRegCore, self).deadline_met():
            return [{ 'link': '/teach/%s/teacherreg' % ( self.program.getUrlBase() ),
                      'text': '%s Teacher Registration' % ( self.program.niceSubName() ),
                      'section': 'teach'}]
        else:
            return []

