
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
from django.contrib.auth.decorators import login_required
from esp.program.models import ClassSubject, ClassSection, Program
from esp.users.models import UserBit, ESPUser, shirt_sizes, shirt_types
from django.contrib.auth.models import User
from django.core.cache import cache
import math

class KeyDoesNotExist(Exception):
    pass

class AdminVitals(ProgramModuleObj):
    doc = """ This allows you to view the major numbers for your program on the main page.
        This will present itself below the options in a neat little table. """

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Admin Module for Showing Basic Vitals",
            "link_title": "Program Vitals",
            "module_type": "manage",
            "seq": -2,
            "main_call": "vitals"
            }
    
    def prepare(self, context=None):
        import operator

        if context is None: context = {}
        
        classes = self.program.classes().select_related()
        vitals = {'classtotal': classes}

        vitals['classsections'] = self.program.sections().select_related()
        vitals['classapproved'] = classes.filter(status=10)
        vitals['classunreviewed'] = classes.filter(status=0)
        vitals['classrejected'] = classes.filter(status=-10)

        proganchor = self.program_anchor_cached()
        
        #   Display pretty labels for teacher and student numbers
        teacher_labels_dict = {}
        for module in self.program.getModules():
            teacher_labels_dict.update(module.teacherDesc())
        vitals['teachernum'] = []
        for key in self.program.teachers().keys():
            if key in teacher_labels_dict:
                vitals['teachernum'].append((teacher_labels_dict[key], self.program.teachers()[key]))
            else:
                vitals['teachernum'].append((key, self.program.teachers()[key]))
                
        student_labels_dict = {}
        for module in self.program.getModules():
            student_labels_dict.update(module.studentDesc())      
        vitals['studentnum'] = []
        for key in self.program.students().keys():
            if key in student_labels_dict:
                vitals['studentnum'].append((student_labels_dict[key], self.program.students()[key]))
            else:
                vitals['studentnum'].append((key, self.program.students()[key]))
                
        timeslots = self.program.getTimeSlots()
        vitals['timeslots'] = []
        
        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.short_description}
            
            curclasses = ClassSection.objects.filter(parent_class__parent_program = self.program,
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
        
        # Cache this; we don't want to walk over all registered students and teachers every page load
        key = "SHIRT_STATS__%d" % self.program.id
        adminvitals_shirt = cache.get(key)
        if adminvitals_shirt is None:
            # List of students' t-shirt sizes as indicated in their profiles. Currently parasitizing vitals.
            shirt_count = {}
            shirts = {}
            for shirt_type in shirt_types:
                shirt_count[ shirt_type[0] ] = {}
                for shirt_size in shirt_sizes:
                    shirt_count[ shirt_type[0] ][ shirt_size[0] ] = 0
# removing this since students don't actually have t-shirt info anymore --rye 02-18-09
#
#            student_dict = self.program.students()
#            if student_dict.has_key('classreg'):
#                for student in student_dict['classreg']:
#                    profile = ESPUser(student).getLastProfile().student_info
#                    if profile is not None:
#                        if shirt_count.has_key(profile.shirt_type) and shirt_count[profile.shirt_type].has_key(profile.shirt_size):
#                            shirt_count[ profile.shirt_type ][ profile.shirt_size ] += 1
#                shirts['students'] = [ { 'type': shirt_type[1], 'distribution':[ shirt_count[shirt_type[0]][shirt_size[0]] for shirt_size in shirt_sizes ] } for shirt_type in shirt_types ]

#            for shirt_type in shirt_types:
#                for shirt_size in shirt_sizes:
#                    shirt_count[ shirt_type[0] ][ shirt_size[0] ] = 0
            teacher_dict = self.program.teachers()
            if teacher_dict.has_key('class_approved'):
                for teacher in teacher_dict['class_approved']:
                    profile = ESPUser(teacher).getLastProfile().teacher_info
                    if profile is not None:
                        if shirt_count.has_key(profile.shirt_type) and shirt_count[profile.shirt_type].has_key(profile.shirt_size):
                            shirt_count[ profile.shirt_type ][ profile.shirt_size ] += 1
            shirts['teachers'] = [ { 'type': shirt_type[1], 'distribution':[ shirt_count[shirt_type[0]][shirt_size[0]] for shirt_size in shirt_sizes ] } for shirt_type in shirt_types ]

            adminvitals_shirt = {'shirts' : shirts, 'shirt_sizes' : shirt_sizes, 'shirt_types' : shirt_types }
            # Use a timeout for the cache expirey --- expiring it "properly" would be rather messy and hard to maintain
            cache.set(key, adminvitals_shirt, 24*3600)

        context['shirt_sizes'] = adminvitals_shirt['shirt_sizes']
        context['shirt_types'] = adminvitals_shirt['shirt_types']
        context['shirts'] = adminvitals_shirt['shirts']

        shours = 0
        chours = 0
        for section in self.program.sections():
            chours += math.ceil(section.duration)
            if section.parent_class.class_size_max !=0:
                shours += math.ceil(section.duration)*section.parent_class.class_size_max
            else: shours = 0
       
        context['classhours'] = chours
        context['classpersonhours'] = shours
        
        return context
    
 

