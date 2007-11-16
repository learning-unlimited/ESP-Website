
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
from esp.program.models import Class
from esp.web.util import render_to_response
from esp.cal.models import Event

class OnSiteClassList(ProgramModuleObj):

    @needs_onsite
    def classList(self, request, tl, one, two, module, extra, prog):
        """ Display a list of all classes that still have space in them """

        if request.GET.has_key('refresh'):
            refresh_time = request.GET['refresh']
        else:
            refresh_time = 30

        # using .extra() to select all the category text simultaneously
        classes = Class.objects.catalog(self.program)

        #   time_now = datetime.now()
        time_now = datetime.now()
        window_start = time_now + timedelta(-1, 85800)
        window_end = time_now + timedelta(0, 3000)
        curtime = Event.objects.filter(start__gte=window_start, start__lte=window_end)
        if curtime.count() > 0:
            curtime = curtime[0]
        else:
            curtime = 'Any Time'
        
        categories = {}
        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt}
        
        return render_to_response(self.baseDir()+'classlist.html', request, (prog, tl), 
            {'prog': prog, 'refresh_time': refresh_time, 'current_time': curtime, 'classes': classes, 'one': one, 'two': two, 'categories': categories.values()})

    @needs_onsite
    def allClassList(self, request, tl, one, two, module, extra, prog):
        """ Display a list of all classes that still have space in them """

        # using .extra() to select all the category text simultaneously
        classes = [(i.num_students()/i.class_size_max, i) for i in Class.objects.catalog(self.program)]
        classes.sort()
        classes = [i[1] for i in classes]
        
        categories = {}
        for cls in classes:
            categories[cls.category_id] = {'id':cls.category_id, 'category':cls.category_txt}
        
        return render_to_response(self.baseDir()+'allclasslist.html', request, (prog, tl), 
            {'classes': classes, 'one': one, 'two': two, 'categories': categories.values()})


        
