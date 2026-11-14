from __future__ import absolute_import
from unittest import mock

from django.test import RequestFactory

from esp.program.models import ClassCategories
from esp.program.modules.handlers.schedulingcheckmodule import SchedulingCheckRunner, RawSCFormatter
from esp.program.tests import ProgramFrameworkTest


class HungryTeachersTest(ProgramFrameworkTest):
    """ The "hungry teachers" scheduling check should count both teaching and
        moderating (MIT: "observing") when deciding who is busy all lunch. """

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_rooms': 4,
            'num_timeslots': 4, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 4, 'classes_per_teacher': 1, 'sections_per_class': 2,
            })
        super(HungryTeachersTest, self).setUp(*args, **kwargs)

        self.timeslots = list(self.program.getTimeSlots().order_by('start'))
        (self.both_teaching, self.teach_and_moderate,
         self.moderate_once, lunch_teacher) = self.teachers

        def sections_of(teacher):
            cls = teacher.getTaughtClassesFromProgram(self.program).get()
            return cls, list(cls.sections.order_by('id'))

        # Lunch is timeslots 1 and 2: a teacherless "Lunch" class meets in each
        lunch_cls, lunch_secs = sections_of(lunch_teacher)
        lunch_cls.category = ClassCategories.objects.get_or_create(category='Lunch', symbol='L')[0]
        lunch_cls.save()
        lunch_cls.removeTeacher(lunch_teacher)
        lunch_secs[0].assign_meeting_times([self.timeslots[1]])
        lunch_secs[1].assign_meeting_times([self.timeslots[2]])

        # Teaches during both lunch blocks
        cls, self.secs_a = sections_of(self.both_teaching)
        self.secs_a[0].assign_meeting_times([self.timeslots[1]])
        self.secs_a[1].assign_meeting_times([self.timeslots[2]])

        # Teaches during one lunch block, moderates during the other
        cls, self.secs_b = sections_of(self.teach_and_moderate)
        self.secs_b[0].assign_meeting_times([self.timeslots[1]])
        self.secs_b[1].assign_meeting_times([self.timeslots[0]])
        self.secs_a[1].moderators.add(self.teach_and_moderate)

        # Teaches outside lunch, moderates during only one lunch block
        cls, secs_c = sections_of(self.moderate_once)
        secs_c[0].assign_meeting_times([self.timeslots[0]])
        secs_c[1].assign_meeting_times([self.timeslots[3]])
        self.secs_a[0].moderators.add(self.moderate_once)

    def run_check(self):
        request = RequestFactory().get('/')
        with mock.patch('esp.program.modules.handlers.schedulingcheckmodule.get_current_request',
                        return_value=request):
            runner = SchedulingCheckRunner(self.program, formatter=RawSCFormatter())
        return runner.hungry_teachers()

    def test_teaching_and_moderating_both_count(self):
        rows = {row['Username']: row for row in self.run_check()}
        self.assertEqual(set(rows), {self.both_teaching, self.teach_and_moderate})

        gerund = self.program.getModeratorGerund().lower()
        self.assertEqual(rows[self.both_teaching]['Classes over lunch'],
                         'teaching %s, teaching %s' % (self.secs_a[0], self.secs_a[1]))
        self.assertEqual(rows[self.teach_and_moderate]['Classes over lunch'],
                         'teaching %s, %s %s' % (self.secs_b[0], gerund, self.secs_a[1]))

    def test_no_lunch_blocks(self):
        ClassCategories.objects.filter(category='Lunch').delete()
        self.assertEqual(self.run_check(), [])
