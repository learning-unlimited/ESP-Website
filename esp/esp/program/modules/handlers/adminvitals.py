
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
from esp.program.models import ClassSubject, ClassSection, Program, ClassCategories
from esp.program.models.class_ import open_class_category
from esp.users.models import UserBit, ESPUser, shirt_sizes, shirt_types
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.query      import Q
from collections import defaultdict
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
            "inline_template": "vitals.html",
            "seq": -2,
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
        vitals['classcancelled'] = classes.filter(status=-20)

        proganchor = self.program_anchor_cached()
        
        #   Display pretty labels for teacher and student numbers
        teacher_labels_dict = {}
        for module in self.program.getModules():
            teacher_labels_dict.update(module.teacherDesc())
        vitals['teachernum'] = []

        ## Ew, queries in a for loop...
        ## Not much to be done about it, though;
        ## the loop is iterating over a list of independent queries and running each.
        teachers = self.program.teachers()
        for key in teachers.keys():
            if key in teacher_labels_dict:
                vitals['teachernum'].append((teacher_labels_dict[key],         ## Unfortunately, 
teachers[key]))
            else:
                vitals['teachernum'].append((key, teachers[key]))
                
        student_labels_dict = {}
        for module in self.program.getModules():
            student_labels_dict.update(module.studentDesc())      
        vitals['studentnum'] = []

        ## Ew, another set of queries in a for loop...
        ## Same justification, though.
        students = self.program.students()
        for key in students.keys():
            if key in student_labels_dict:
                vitals['studentnum'].append((student_labels_dict[key], students[key]))
            else:
                vitals['studentnum'].append((key, students[key]))
                
        timeslots = self.program.getTimeSlots()
        vitals['timeslots'] = []
        
        ## Prefetch enough data that get_meeting_times() and num_students() don't have to hit the db
        curclasses = ClassSection.prefetch_catalog_data(
            ClassSection.objects.filter(parent_class__parent_program = self.program))

        ## Is it really faster to do this logic in Python?
        ## It'd be even faster to just write a raw SQL query to do it.
        ## But this is probably good enough.
        timeslot_dict = defaultdict(list)
        timeslot_set = set(timeslots)
        for section in curclasses:
            for timeslot in set.intersection(timeslot_set, section.get_meeting_times()):
                timeslot_dict[timeslot].append(section)

        for timeslot in timeslots:
            curTimeslot = {'slotname': timeslot.short_description}
            
            curTimeslot['classcount'] = len(timeslot_dict[timeslot])

            class studentcounter:
                self.clslist = []

                def count(self):
                    lst = [0] + [x.num_students() for x in self.clslist]
                    return reduce(operator.add, lst)

                def max_count(self):
                    lst = [0] + [x.capacity for x in self.clslist]
                    return reduce(operator.add, lst)

                def __init__(self, newclslist):
                    self.clslist = newclslist

            curTimeslot['studentcount'] = studentcounter(timeslot_dict[timeslot])
            
            vitals['timeslots'].append(curTimeslot)

        context['vitals'] = vitals

        adminvitals_shirt = self.program.getShirtInfo()
        context['shirt_sizes'] = adminvitals_shirt['shirt_sizes']
        context['shirt_types'] = adminvitals_shirt['shirt_types']
        context['shirts'] = adminvitals_shirt['shirts']

        shours = 0
        chours = 0
        ## Write this as a 'for' loop because PostgreSQL can't do it in
        ## one go without a subquery or duplicated logic, and Django
        ## doesn't have enough power to expose either approach directly.
        ## At least there aren't any queries in the for loop...
        ## (In MySQL, this could I believe be done with a minimally-painful extra() clause.)
        ## Also, since we're iterating over a big data set, use .values()
        ## minimize the number of objects that we're creating.
        ## One dict and two Decimals per row, as opposed to
        ## an Object per field and all kinds of stuff...
        for cls in self.program.classes().annotate(subject_duration=Sum('sections__duration')).values('subject_duration', 'class_size_max'):
            if cls['subject_duration']:
                chours += cls['subject_duration']
                shours += cls['subject_duration'] * (cls['class_size_max'] if cls['class_size_max'] else 0)
           
        context['classhours'] = chours
        context['classpersonhours'] = shours
        Q_categories = Q(program=self.program)
        crmi = self.program.getModuleExtension('ClassRegModuleInfo')
        if crmi.open_class_registration:
            Q_categories |= Q(pk=open_class_category().pk)
        #   Introduce a separate query to get valid categories, since the single query seemed to introduce duplicates
        program_categories = ClassCategories.objects.filter(Q_categories).distinct().values_list('id', flat=True)
        annotated_categories = ClassCategories.objects.filter(cls__parent_program=self.program, cls__status__gte=0).annotate(num_subjects=Count('cls', distinct=True), num_sections=Count('cls__sections')).order_by('-num_subjects').values('id', 'num_sections', 'num_subjects', 'category').distinct()
        context['categories'] = filter(lambda x: x['id'] in program_categories, annotated_categories)

        return context
    
 


    class Meta:
        abstract = True

