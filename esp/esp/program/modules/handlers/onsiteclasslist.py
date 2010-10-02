
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
from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call, aux_call
from esp.program.models import ClassSubject, ClassSection
from esp.web.util import render_to_response
from esp.cal.models import Event
from esp.cache import cache_function
from esp.users.models import ESPUser
from esp.resources.models import ResourceAssignment
from esp.datatree.models import *
from django.db.models import Min

import colorsys

def hsl_to_rgb(hue, saturation, lightness=0.5):
    (red, green, blue) = colorsys.hls_to_rgb(hue, lightness, saturation)
    return '%02x%02x%02x' % (min(1.0, red) * 255.0, min(1.0, green) * 255.0, min(1.0, blue) * 255.0)

class OnSiteClassList(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Show All Classes at Onsite Registration",
            "link_title": "List of All Classes",
            "module_type": "onsite",
            "seq": 31
            }, {
            "admin_title": "Show Open Classes at Onsite Registration",
            "link_title": "List of Open Classes",
            "module_type": "onsite",
            "seq": 32,
            "main_call": "classList",
            "aux_calls": "status",
            } ]

    
    @cache_function
    def section_data(sec):
        sect = {}
        sect['id'] = sec.id
        sect['emailcode'] = sec.emailcode()
        sect['title'] = sec.title()
        sect['teachers'] = ', '.join([t.name() for t in list(sec.teachers)])
        sect['rooms'] = (' ,'.join(sec.prettyrooms()))[:12]
        return sect
    section_data.depend_on_model(lambda: ResourceAssignment)
    section_data.depend_on_cache(lambda: ClassSubject.teachers, lambda **kwargs: {})
    section_data = staticmethod(section_data)

    @needs_onsite
    def status(self, request, tl, one, two, module, extra, prog):
        context = {}
        msgs = []
        if request.method == 'POST':
            if 'op' in request.GET and request.GET['op'] == 'add' and 'sec_id' in request.GET:
                try:
                    sec = ClassSection.objects.get(id=request.GET['sec_id'])
                    print 'Got section %s' % sec
                except:
                    sec = None
                user = None
                if sec and 'add_%s' % sec.id in request.POST:
                    try:
                        user_id = int(request.POST['add_%s' % sec.id])
                        user = ESPUser.objects.get(id=user_id)
                        print 'Got user %s' % user
                    except:
                        user = None
                if sec and user:
                    #   Find out what other classes the user was taking during the times of this section
                    removed_classes = []
                    schedule = user.getEnrolledSections(prog)
                    print 'Got schedule %s' % schedule
                    if sec in schedule:
                        #   If they were in the specified section, take them out.
                        sec.unpreregister_student(user)
                        msgs.append('Removed %s (%d) from %s' % (user.name(), user.id, sec))
                    else:
                        #   Otherwise take them out of whatever they were in and put them in.
                        target_times = sec.meeting_times.all().values_list('id', flat=True)
                        for s in schedule:
                            if s.meeting_times.filter(id__in=target_times).count() > 0:
                                s.unpreregister_student(user)
                                msgs.append('Removed %s (%d) from %s' % (user.name(), user.id, s))
                        sec.preregister_student(user, overridefull=True)
                        msgs.append('Added %s (%d) to %s' % (user.name(), user.id, sec))
        context['msgs'] = msgs
        
        reg_counts = prog.student_counts_by_section_id()
        capacity_counts = prog.capacity_by_section_id()
        checkin_counts = prog.checked_in_by_section_id()
        all_sections = prog.sections()
    
        timeslots = []
        for timeslot in prog.getTimeSlots():
            item = {}
            item['timeslot'] = timeslot
            item['sections'] = []
            sections = all_sections.filter(meeting_times=timeslot)
            for sec in sections:
                sect = OnSiteClassList.section_data(sec)
                
                if sec.id in reg_counts and reg_counts[sec.id]:
                    sect['reg_count'] = reg_counts[sec.id]
                else:
                    sect['reg_count'] = 0
                if sec.id in capacity_counts:
                    sect['capacity_count'] = capacity_counts[sec.id]
                else:
                    sect['capacity_count'] = 0
                if sec.id in checkin_counts:
                    sect['checkin_count'] = checkin_counts[sec.id]
                else:
                    sect['checkin_count'] = 0
                
                if sect['capacity_count'] > 0:
                    hue_redness = sect['reg_count'] / float(sect['capacity_count'])
                else:
                    hue_redness = 0.5
                if sect['reg_count'] > 0:
                    lightness = sect['checkin_count'] / float(sect['reg_count'])
                else:
                    lightness = 0.0
                sect['color'] = hsl_to_rgb(0.4 + 0.6 * hue_redness, 0.8, 0.9 - 0.5 * lightness)
                
                item['sections'].append(sect)
            timeslots.append(item)
        context['timeslots'] = timeslots
        response = render_to_response(self.baseDir()+'status.html', request, (prog, tl), context)
        return response

    @needs_onsite
    def classList(self, request, tl, one, two, module, extra, prog):
        """ Display a list of all classes that still have space in them """
        context = {}
        defaults = {'refresh': 120, 'scrollspeed': 1}
        for key_option in defaults.keys():
            if request.GET.has_key(key_option):
                context[key_option] = request.GET[key_option]
            else:
                context[key_option] = defaults[key_option]

        time_now = datetime.now()
        window_start = time_now + timedelta(-1, 85200)
        curtime = Event.objects.filter(start__gte=window_start).order_by('start')
        if curtime:
            curtime = curtime[0]
            classes = self.program.sections().annotate(begin_time=Min("meeting_times__start")).filter(
                status=10, parent_class__status=10,
                begin_time__gte=curtime.start
                ).order_by('parent_class__category', 'begin_time').distinct()
        else:
            curtime = None
            classes = []
        
        context.update({'prog': prog, 'current_time': curtime, 'classes': classes, 'one': one, 'two': two})
        
        return render_to_response(self.baseDir()+'classlist.html', request, (prog, tl), context)

    @main_call
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


        
