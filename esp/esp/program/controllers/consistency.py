
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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
  Email: web-team@learningu.org
"""

from esp.program.models import Program, ClassSection, ClassSubject


class ConsistencyChecker(object):
    """ A class for finding issues with the scheduling of a program. """
    def __init__(self, program, *args, **kwargs):
        self.program = program
        
        self.classes = ClassSubject.objects.filter(parent_program=self.program)
        teachers = set()
        for c in self.classes:
            teachers = teachers.union(c.get_teachers())
        self.teachers = list(teachers)
        self.sections = ClassSection.objects.filter(parent_class__parent_program=self.program)

    def check_expected_duration(self, section):
        """ Checking: Every class section has the expected duration. """
        result = []
        expected_duration = int(round(section.duration)) # assumes each event slot = 1hr
        actual_duration = len(section.get_meeting_times())
        if expected_duration != actual_duration and actual_duration > 0:  # >0 to avoid unscheduled classes
            result.append(str(section.emailcode()) + ' has expected duration ' + str(expected_duration) + ', actual duration ' + str(actual_duration))
        return result

    def check_teacher_conflict(self, teacher):
        result = []
        sections_taught = list(teacher.getTaughtSectionsFromProgram(self.program)) # I don't trust the QuerySet to iterate in the same order for both loops.
        for i in range(0, len(sections_taught)):
            s1 = sections_taught[i]
            c1_times = s1.get_meeting_times()
            if len(c1_times) == 0:
                continue
            for j in range(i+1, len(sections_taught)):
                s2 = sections_taught[j]
                c2_times = s2.get_meeting_times()
                if len(c2_times) > 0:
                    if set(c1_times).intersection(c2_times) != set():
                        result.append(str(s1.emailcode()) + ' and ' + str(s2.emailcode()) + ' are both taught by ' + str(teacher) + ' at ' + ', '.join([str(x) for x in set(c1_times).intersection(c2_times)]))
        return result
    
    def check_resource_conflicts(self):
        # TODO: check locations
        result = []
        sectionlist = list(self.sections)   # I don't trust the QuerySet to iterate in the same order for both loops.
        numsections = len(sectionlist)
        count=0
        for i in range(0,numsections):
            s1 = sectionlist[i]
            s1_used_resources = set(s1.getResources())
            if len(s1_used_resources) == 0:
                continue
            for j in range(i+1, numsections):
                s2 = sectionlist[j]
                s2_used_resources = set(s2.getResources())
                if len(s2_used_resources) > 0:
                    if s1_used_resources.intersection(s2_used_resources) != set():
                        result.append(str(s1.emailcode()) + ' and ' + str(s2.emailcode()) + ' are both using: ' + str([[x.name, x.event] for x in set(s1_used_resources).intersection(s2_used_resources)]))
        return result
        
    def run_all_checks(self):
        results = []
        for section in self.sections:
            results += self.check_expected_duration(section)
        for teacher in self.teachers:
            results += self.check_teacher_conflict(teacher)
        results += self.check_resource_conflicts()
        return results
