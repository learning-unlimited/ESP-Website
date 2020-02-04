
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from esp.program.models import Program, ClassSection, ClassSubject, BooleanExpression, ScheduleConstraint, ScheduleTestOccupied, ScheduleTestCategory, ClassCategories

import datetime

class LunchConstraintGenerator(object):
    """ A class for finding issues with the scheduling of a program. """
    def __init__(self, program, lunch_timeslots=[], generate_constraints=True, include_conditions=True, autocorrect=True, **kwargs):
        self.program = program
        self.generate_constraints = generate_constraints
        self.include_conditions = include_conditions
        self.autocorrect = autocorrect

        #   Figure out which timeslots are before, during and after lunch on each day
        self.days = {}
        all_timeslots = self.program.getTimeSlots()
        past_lunch = False
        lunch_timeslots = list(lunch_timeslots)
        lunch_timeslots.sort(key=lambda x: x.start)
        for timeslot in all_timeslots:
            day = datetime.date(timeslot.start.year, timeslot.start.month, timeslot.start.day)
            if day not in self.days:
                past_lunch = False
                self.days[day] = {'before': [], 'lunch': [], 'after': []}
            if timeslot in lunch_timeslots:
                self.days[day]['lunch'].append(timeslot)
                past_lunch = True
            else:
                if past_lunch:
                    self.days[day]['after'].append(timeslot)
                else:
                    self.days[day]['before'].append(timeslot)

    def clear_existing_constraints(self):
        for lunch in ClassSubject.objects.filter(parent_program__id=self.program.id, category=self.get_lunch_category()):
            lunch.delete()
        for constraint in ScheduleConstraint.objects.filter(program=self.program):
            for boolexp in [constraint.condition, constraint.requirement]:
                boolexp.delete()
            constraint.delete()

    def apply_binary_op_to_list(self, expression, operator_text, identity_value, tokens):
        """ Add the appropriate boolean tokens to 'expression' so
            that the operator in 'operator_text' is applied over all
            items in 'tokens'
        """

        #   If there are 0 tokens in the list, do nothing
        if len(tokens) == 0:
            pass
        #   If there is 1 token in the list, apply the operator to it and the identity.
        elif len(tokens) == 1:
            expression.add_token(tokens.pop())
            expression.add_token(identity_value)
            expression.add_token(operator_text)
        #   If there are 2 tokens in the list, apply the operator to those tokens.
        elif len(tokens) == 2:
            expression.add_token(tokens.pop())
            expression.add_token(tokens.pop())
            expression.add_token(operator_text)
        #   If there are more than 2 tokens in the list, divide the list in half and work recursively
        else:
            midpoint = len(tokens) / 2
            first_half = tokens[:midpoint]
            second_half = tokens[midpoint:]
            self.apply_binary_op_to_list(expression, operator_text, identity_value, first_half)
            self.apply_binary_op_to_list(expression, operator_text, identity_value, second_half)
            expression.add_token(operator_text)

        return expression

    def get_lunch_category(self):
        qs = ClassCategories.objects.filter(category='Lunch', symbol='L').order_by('-id')
        if qs.exists():
            lunch_category = qs[0]
        else:
            lunch_category, created = ClassCategories.objects.get_or_create(category='Lunch', symbol='L')
        self.program.class_categories.add(lunch_category)
        return lunch_category

    def get_lunch_subject(self, day):
        """ Locate lunch subject with the appropriate day in the 'message for directors' field. """

        category = self.get_lunch_category()
        lunch_subjects = ClassSubject.objects.filter(parent_program__id=self.program.id, category=self.get_lunch_category(), message_for_directors=day.isoformat())
        lunch_subject = None
        example_timeslot = self.days[day]['lunch'][0]
        timeslot_length = (example_timeslot.duration()).total_seconds() / 3600.0

        if lunch_subjects.count() == 0:
            #   If no lunch was found, create a new subject
            new_subject = ClassSubject()
            new_subject.grade_min = 7
            new_subject.grade_max = 12
            new_subject.parent_program = self.program
            new_subject.category = category
            new_subject.class_info = 'Enjoy a break for lunch with your friends!  Please register for at least one lunch period on each day of the program.'
            new_subject.class_size_min = 0
            # If the program doesn't have a max size, we unfortunately still
            # need one here.  Set a really big one.
            new_subject.class_size_max = self.program.program_size_max or 10**6
            new_subject.status = 10
            new_subject.duration = '%.4f' % timeslot_length
            new_subject.message_for_directors = day.isoformat()
            new_subject.save()
            new_subject.title = 'Lunch Period'
            new_subject.save()
            lunch_subject = new_subject
        else:
            #   Otherwise, return an existing lunch subject
            lunch_subject = lunch_subjects[0]
        return lunch_subject

    def get_lunch_sections(self, day):

        lunch_subject = self.get_lunch_subject(day)
        for timeslot in self.days[day]['lunch']:
            lunch_sections = lunch_subject.sections.filter(meeting_times__id=timeslot.id)
            if lunch_sections.count() == 0:
                new_section = lunch_subject.add_section(status=10)
                new_section.meeting_times.add(timeslot)
            else:
                for sec in lunch_sections:
                    sec.status = 10
                    sec.save()

        return self.get_lunch_subject(day).get_sections()

    def get_failure_function(self, day):
        on_failure_code = """
# This code is part of a function: on_failure(schedule_map)
# The function should return a tuple containing the new schedule
# map as its first element.  (Messages provided in the second
# element are ignored since the default error handling was deemed
# sufficient, but this can be changed by uncommenting some code.)

# Application specific: IDs of lunch periods for this constraint
lunch_choices = %s

# Compute list of feasible options for student's lunch period
availability = [(len(schedule_map.map[x]) == 0) for x in lunch_choices]
time_options = []
for i in range(len(lunch_choices)):
    if availability[i]: time_options.append(lunch_choices[i])

# Choose a lunch period, find classes in available times
if len(time_options) == 0:
    return (schedule_map, 'Unable to autoschedule lunch.')
else:
    dest_sec = None
    dest_qs = ClassSection.objects.filter(meeting_times__id__in=time_options, parent_class__category__category='Lunch')
    if dest_qs.count() == 0:
        return (schedule_map, 'Unable to autoschedule lunch.')
    elif dest_qs.count() == 1:
        dest_sec = dest_qs[0]
    else:
        dest_sec = random.choice(list(dest_qs))
    rets = dest_sec.preregister_student(schedule_map.user, overridefull=True)
    schedule_map.add_section(dest_sec)
    data = str(schedule_map.map)
    return (schedule_map, data)
""" % [x.id for x in self.days[day]['lunch']]
        return on_failure_code

    def generate_constraint(self, day):
        #   Prepare empty expression objects
        exp_requirement = BooleanExpression()
        exp_requirement.label = 'choose a lunch period on %s' % day.strftime('%A')
        exp_requirement.save()

        exp_check = BooleanExpression()
        exp_check.label = '%s lunch constraint check for %s' % (self.program.niceName(), day.isoformat())
        exp_check.save()

        constraint = ScheduleConstraint()
        constraint.program = self.program
        constraint.condition = exp_check
        constraint.requirement = exp_requirement
        if self.autocorrect:
            constraint.on_failure = self.get_failure_function(day)
        constraint.save()

        #   Build schedule tests using BooleanExpressions
        seq_id = 0

        lunch_tests = []
        for timeslot in self.days[day]['lunch']:
            new_test = ScheduleTestCategory()
            new_test.timeblock_id = timeslot.id
            new_test.exp_id = exp_requirement.id
            new_test.category = self.get_lunch_category()
            lunch_tests.append(new_test)
            seq_id += 1
        self.apply_binary_op_to_list(exp_requirement, 'OR', '0', lunch_tests)

        if self.include_conditions:
            #   Add conditions so the students are only required to have lunch if they have
            #   classes both before and after lunch
            morning_tests = []
            for timeslot in self.days[day]['before']:
                new_test = ScheduleTestOccupied()
                new_test.timeblock_id = timeslot.id
                new_test.exp_id = exp_check.id
                morning_tests.append(new_test)
                seq_id += 1
            self.apply_binary_op_to_list(exp_check, 'OR', '0', morning_tests)

            afternoon_tests = []
            for timeslot in self.days[day]['after']:
                new_test = ScheduleTestOccupied()
                new_test.timeblock_id = timeslot.id
                new_test.exp_id = exp_check.id
                afternoon_tests.append(new_test)
                seq_id += 1
            self.apply_binary_op_to_list(exp_check, 'OR', '0', afternoon_tests)

            #   Add an AND to the exp_check so that it requires both a morning class and an afternoon class
            exp_check.add_token('AND')
        else:
            #   Make the check always true (e.g. students must always have a lunch period)
            exp_check.add_token('1')

    def generate_all_constraints(self):
        self.clear_existing_constraints()
        for day in self.days:
            if not self.days[day]['lunch']: # no lunch timeblocks
                continue
            self.get_lunch_subject(day)
            self.get_lunch_sections(day)
            if self.generate_constraints:
                self.generate_constraint(day)

