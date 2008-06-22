
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
from esp.program.models import ClassSubject, ClassSection, Program
from esp.users.models import UserBit, ESPUser, shirt_sizes, shirt_types
from django.contrib.auth.models import User
from django.core.cache import cache

class KeyDoesNotExist(Exception):
    pass

class AdminVitals(ProgramModuleObj):
    doc = """ This allows you to view the major numbers for your program on the main page.
        This will present itself below the options in a neat little table. """
        
    def prepare(self, context=None):
        import operator

        if context is None: context = {}
        
        classes = self.program.classes().select_related()
        vitals = {'classtotal': classes}
        
        vitals['classapproved'] = classes.filter(status=10)
        vitals['classunreviewed'] = classes.filter(status=0)
        vitals['classrejected'] = classes.filter(status=-10)

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
            
            curclasses = ClassSection.objects.filter(classsubject__parent_program = self.program,
                                              meeting_times  = timeslot)

            curTimeslot['classcount'] = curclasses

            class studentcounter:
                self.clslist = []

                def count(self):
                    lst = [x.num_students() for x in self.clslist]
                    return reduce(operator.add, lst)

                def max_count(self):
                    lst = [x.capacity for x in self.clslist]
                    return reduce(operator.add, lst)

                def __init__(self, newclslist):
                    self.clslist = newclslist

            curTimeslot['studentcount'] = studentcounter(curclasses)
            
            vitals['timeslots'].append(curTimeslot)

        context['vitals'] = vitals
        
        # List of students' t-shirt sizes as indicated in their profiles. Currently parasitizing vitals.
        shirt_count = {}
        shirts = {}
        for shirt_type in shirt_types:
            shirt_count[ shirt_type[0] ] = {}
            for shirt_size in shirt_sizes:
                shirt_count[ shirt_type[0] ][ shirt_size[0] ] = 0
        student_dict = self.program.students()
        if student_dict.has_key('classreg'):
            for student in student_dict['classreg']:
                profile = ESPUser(student).getLastProfile().student_info
                if profile is not None:
                    if shirt_count.has_key(profile.shirt_type) and shirt_count[profile.shirt_type].has_key(profile.shirt_size):
                        shirt_count[ profile.shirt_type ][ profile.shirt_size ] += 1
            shirts['students'] = [ { 'type': shirt_type[1], 'distribution':[ shirt_count[shirt_type[0]][shirt_size[0]] for shirt_size in shirt_sizes ] } for shirt_type in shirt_types ]
        
        for shirt_type in shirt_types:
            for shirt_size in shirt_sizes:
                shirt_count[ shirt_type[0] ][ shirt_size[0] ] = 0
        for teacher in self.program.teachers()['class_approved']:
            profile = ESPUser(teacher).getLastProfile().teacher_info
            if profile is not None:
                if shirt_count.has_key(profile.shirt_type) and shirt_count[profile.shirt_type].has_key(profile.shirt_size):
                    shirt_count[ profile.shirt_type ][ profile.shirt_size ] += 1
        shirts['teachers'] = [ { 'type': shirt_type[1], 'distribution':[ shirt_count[shirt_type[0]][shirt_size[0]] for shirt_size in shirt_sizes ] } for shirt_type in shirt_types ]
        context['shirt_sizes'] = shirt_sizes
        context['shirt_types'] = shirt_types
        context['shirts'] = shirts
        
        return context
    
 

