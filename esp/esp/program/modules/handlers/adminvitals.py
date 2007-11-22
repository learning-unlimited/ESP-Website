
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.program.models import Class, Program
from esp.users.models import UserBit, ESPUser
from django.contrib.auth.models import User

class AdminVitals(ProgramModuleObj):
    doc = """ This allows you to view the major numbers for your program on the main page.
        This will present itself below the options in a neat little table. """
        
    def prepare(self, context=None):
        import operator

        if context is None: context = {}
        
        classes = self.program.classes().select_related()
        vitals = {'classtotal': classes.count()}
        
        vitals['classapproved'] = classes.filter(status=10).count()
        vitals['classunreviewed'] = classes.exclude(status=0).count()

        vitals['classrejected'] = vitals['classtotal'] - vitals['classapproved'] - vitals['classunreviewed']


        proganchor = self.program_anchor_cached()

        vitals['teachernum'] = self.program.teachers().items()
#        vitals['teachernum'].append(('total', # students_union generates a stupidly expensive query; need something better, possibly "all Students with a UserBit Q inside this program"
                                     # self.program.teachers_union()))
        vitals['studentnum'] = self.program.students().items()
#        vitals['studentnum'].append(('total', # students_union generates a stupidly expensive query; need something better, possibly "all Students with a UserBit Q inside this program"
                                     # self.program.students_union()))
        
        timeslots = self.program.getTimeSlots()

        vitals['timeslots'] = []
        
        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.short_description}
            
            curclasses = Class.objects.filter(parent_program = self.program,
                                              meeting_times  = timeslot)

            curTimeslot['classcount'] = len(curclasses)

            if curTimeslot['classcount'] == 0:
                curTimeslot['studentcount'] = 0
            else: 
                curTimeslot['studentcount'] = \
                      reduce(operator.add, [x.num_students() for x in curclasses ])
            
            vitals['timeslots'].append(curTimeslot)

        context['vitals'] = vitals
        
        return context
    
 

