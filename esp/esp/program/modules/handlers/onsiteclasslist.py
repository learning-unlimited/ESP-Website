
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

from datetime import datetime, timedelta
from esp.program.modules.base import ProgramModuleObj, needs_onsite
from esp.program.models import ClassSubject, ClassSection
from esp.web.util import render_to_response
from esp.cal.models import Event
from esp.datatree.models import GetNode

class OnSiteClassList(ProgramModuleObj):

    @needs_onsite
    def classList(self, request, tl, one, two, module, extra, prog):
        """ Display a list of all classes that still have space in them """
        def cmp_class(one, other):
            if cmp(one.category.id, other.category.id) != 0:
                return cmp(one.category.id, other.category.id)
            else:
                return cmp(one.start_time(), other.start_time())

        def cmp_section(one, other):
            p1 = one.parent_class
            p2 = other.parent_class
            if cmp(p1.category.id, p2.category.id) != 0:
                return cmp(p1.category.id, p2.category.id)
            else:
                return cmp(one.start_time(), other.start_time())

        context = {}
        defaults = {'refresh': 30, 'scrollspeed': 3}
        for key_option in defaults.keys():
            if request.GET.has_key(key_option):
                context[key_option] = request.GET[key_option]
            else:
                context[key_option] = defaults[key_option]

        classes = list(self.program.sections())
        classes.sort(cmp=cmp_section)

        time_now = datetime.now()
        window_start = time_now + timedelta(-1, 85800)
        window_end = time_now + timedelta(0, 3000)
        curtime = Event.objects.filter(start__gte=window_start, start__lte=window_end)
        if curtime.count() > 0:
            curtime = curtime[0]
        else:
            curtime = None
        
        categories = {}
        for sec in classes:
            categories[sec.parent_class.category_id] = {'id': sec.parent_class.category_id, 'category': sec.parent_class.category.category}

        printers = [ x.name for x in GetNode('V/Publish/Print').children() ]

        context.update({'prog': prog, 'current_time': curtime, 'classes': classes, 'one': one, 'two': two, 'categories': categories.values(), 'printers': printers})
        
        return render_to_response(self.baseDir()+'classlist.html', request, (prog, tl), context)

    @needs_onsite
    def allClassList(self, request, tl, one, two, module, extra, prog):
        """ Display a list of all classes that still have space in them """

        #   This view still uses classes, not sections.  The templates show information
        #   for each section of each class.
        classes = [(i.num_students()/(i.class_size_max + 1), i) for i in self.program.classes()]
        classes.sort()
        classes = [i[1] for i in classes]
        
        categories = {}
        for cls in classes:
            categories[cls.category_id] = {'id': cls.category_id, 'category': cls.category.category}

        printers = [ x.name for x in GetNode('V/Publish/Print').children() ]
        
        return render_to_response(self.baseDir()+'allclasslist.html', request, (prog, tl), 
            {'classes': classes, 'prog': self.program, 'one': one, 'two': two, 'categories': categories.values(), 'printers': printers})


        
