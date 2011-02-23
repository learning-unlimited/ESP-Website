
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
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

        adminvitals_shirt = self.program.getShirtInfo()
        context['shirt_sizes'] = adminvitals_shirt['shirt_sizes']
        context['shirt_types'] = adminvitals_shirt['shirt_types']
        context['shirts'] = adminvitals_shirt['shirts']

        shours = 0
        chours = 0
        for section in self.program.sections():
            chours += math.ceil(section.duration)
            if type(section.parent_class.class_size_max) == int:
                shours += math.ceil(section.duration)*section.parent_class.class_size_max
            else: shours = 0
       
        context['classhours'] = chours
        context['classpersonhours'] = shours
        
        return context
    
 

