__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
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

import datetime

from esp.cal.models import Event, EventType
from esp.program.models import (BooleanExpression, BooleanToken, ClassCategories, ClassSection,
                                ScheduleConstraint, ScheduleTestCategory, StudentRegistration,
                                autocorrect_schedule, unrepairable_requirements)
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class StudentLunchSelectionTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3,
            'timeslot_length': 50,
            'timeslot_gap': 10,
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
            'num_students': 3,
        })
        super().setUp(*args, **kwargs)
        self.add_student_profiles()

        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        pm = ProgramModule.objects.get(handler='StudentLunchSelection', module_type='learn')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.module.user = self.students[0]

        self.lunch_category, _ = ClassCategories.objects.get_or_create(
            category='Lunch',
            is_lunch=True,
            defaults={'symbol': 'L'},
        )

        self.lunch_event_type, _ = EventType.objects.get_or_create(
            description='Lunch',
        )

        program_dates = self.program.dates()
        self.lunch_day = program_dates[0] if program_dates else datetime.date.today()
        lunch_start = datetime.datetime.combine(self.lunch_day, datetime.time(12, 0))
        lunch_end   = lunch_start + datetime.timedelta(hours=1)
        self.lunch_event = Event.objects.create(
            program=self.program,
            event_type=self.lunch_event_type,
            start=lunch_start,
            end=lunch_end,
            short_description='Lunch 12:00',
            description='Lunch 12:00',
        )

        # Create a lunch ClassSubject and ClassSection linked to the timeslot
        from esp.program.models import ClassSubject
        self.lunch_class = ClassSubject.objects.create(
            title='Lunch',
            category=self.lunch_category,
            parent_program=self.program,
            grade_min=7,
            grade_max=12,
            class_size_max=100,
            duration='1.0',
        )
        self.lunch_section = ClassSection.objects.create(
            parent_class=self.lunch_class,
            duration='1.0',
            max_class_capacity=100,
        )
        self.lunch_section.meeting_times.add(self.lunch_event)

        self.student = self.students[0]

    def tearDown(self):
        StudentRegistration.objects.filter(
            section__parent_class__category=self.lunch_category,
        ).delete()
        Record.objects.filter(program=self.program, event__name='lunch_selected').delete()
        self.lunch_section.meeting_times.clear()
        self.lunch_section.delete()
        self.lunch_class.delete()
        self.lunch_event.delete()
        super().tearDown()

    def test_isStep_true_when_lunch_events_exist(self):
        self.assertTrue(self.module.isStep())

    def test_isStep_false_when_no_lunch_events(self):
        self.lunch_section.meeting_times.clear()
        self.assertFalse(self.module.isStep())

    def test_isCompleted_false_before_selection(self):
        self.assertFalse(self.module.isCompleted(self.student))

    def test_isCompleted_true_after_record_created(self):
        rt, _ = RecordType.objects.get_or_create(name='lunch_selected')
        Record.objects.get_or_create(user=self.student, program=self.program, event=rt)
        self.assertTrue(self.module.isCompleted(self.student))

    def test_select_lunch_get_renders_for_eligible_student(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
            "Couldn't log in as student %s" % self.student.username,
        )
        response = self.client.get(self.module.get_full_path())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'form', response.content.lower())

    def test_select_lunch_get_blocked_for_anonymous_user(self):
        self.client.logout()
        response = self.client.get(self.module.get_full_path())
        self.assertNotEqual(response.status_code, 200)

    def test_select_lunch_get_blocked_for_teacher(self):
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username,
        )
        response = self.client.get(self.module.get_full_path())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'timeslot', response.content)

    def test_select_lunch_get_shows_lunch_timeslot(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        response = self.client.get(self.module.get_full_path())
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            self.lunch_event.short_description.encode(),
            response.content,
            "Expected lunch timeslot description in GET response",
        )

    def test_select_lunch_post_valid_selection_redirects(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        dates = self.program.dates()
        post_data = {}
        for i, day in enumerate(dates):
            if day == self.lunch_day:
                post_data['day%d-timeslot' % i] = self.lunch_event.id
            else:
                post_data['day%d-timeslot' % i] = -1
        response = self.client.post(self.module.get_full_path(), data=post_data)
        self.assertEqual(response.status_code, 302)

    def test_select_lunch_post_valid_selection_creates_registration(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        dates = self.program.dates()
        post_data = {}
        for i, day in enumerate(dates):
            if day == self.lunch_day:
                post_data['day%d-timeslot' % i] = self.lunch_event.id
            else:
                post_data['day%d-timeslot' % i] = -1
        self.client.post(self.module.get_full_path(), data=post_data)
        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=self.student,
                section=self.lunch_section,
            ).exists(),
            "Expected a StudentRegistration for the lunch section after valid POST",
        )

    def test_select_lunch_post_valid_selection_sets_completed(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        dates = self.program.dates()
        post_data = {}
        for i, day in enumerate(dates):
            if day == self.lunch_day:
                post_data['day%d-timeslot' % i] = self.lunch_event.id
            else:
                post_data['day%d-timeslot' % i] = -1
        self.client.post(self.module.get_full_path(), data=post_data)
        self.assertTrue(
            self.module.isCompleted(self.student),
            "isCompleted() should be True after a successful lunch selection",
        )

    def test_select_lunch_post_decline_redirects(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        dates = self.program.dates()
        post_data = {'day%d-timeslot' % i: -1 for i in range(len(dates))}
        response = self.client.post(self.module.get_full_path(), data=post_data)
        self.assertEqual(response.status_code, 302)

    def test_select_lunch_post_decline_creates_no_registration(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        dates = self.program.dates()
        post_data = {'day%d-timeslot' % i: -1 for i in range(len(dates))}
        self.client.post(self.module.get_full_path(), data=post_data)
        self.assertFalse(
            StudentRegistration.valid_objects().filter(
                user=self.student,
                section__parent_class__category=self.lunch_category,
            ).exists(),
            "No lunch StudentRegistration should exist after declining lunch",
        )

    def test_select_lunch_post_reselection_replaces_previous(self):
        lunch_start2 = datetime.datetime.combine(self.lunch_day, datetime.time(13, 0))
        lunch_end2   = lunch_start2 + datetime.timedelta(hours=1)
        lunch_event2 = Event.objects.create(
            program=self.program,
            event_type=self.lunch_event_type,
            start=lunch_start2,
            end=lunch_end2,
            short_description='Lunch 13:00',
            description='Lunch 13:00',
        )
        lunch_section2 = ClassSection.objects.create(
            parent_class=self.lunch_class,
            duration='1.0',
            max_class_capacity=100,
        )
        lunch_section2.meeting_times.add(lunch_event2)

        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        dates = self.program.dates()

        post_data = {}
        for i, day in enumerate(dates):
            if day == self.lunch_day:
                post_data['day%d-timeslot' % i] = self.lunch_event.id
            else:
                post_data['day%d-timeslot' % i] = -1
        self.client.post(self.module.get_full_path(), data=post_data)
        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=self.student, section=self.lunch_section,
            ).exists()
        )

        post_data2 = {}
        for i, day in enumerate(dates):
            if day == self.lunch_day:
                post_data2['day%d-timeslot' % i] = lunch_event2.id
            else:
                post_data2['day%d-timeslot' % i] = -1
        self.client.post(self.module.get_full_path(), data=post_data2)

        self.assertFalse(
            StudentRegistration.valid_objects().filter(
                user=self.student, section=self.lunch_section,
            ).exists(),
            "Old lunch registration should be removed on re-selection",
        )
        self.assertTrue(
            StudentRegistration.valid_objects().filter(
                user=self.student, section=lunch_section2,
            ).exists(),
            "New lunch registration should exist after re-selection",
        )

        lunch_section2.meeting_times.clear()
        lunch_section2.delete()
        lunch_event2.delete()

    def require_lunch(self, enforce, autocorrect=False, timeblocks=None):
        """A constraint requiring a lunch-category class in one of these blocks."""
        timeblocks = timeblocks or [self.lunch_event]
        condition = BooleanExpression.objects.create(label='always')
        BooleanToken.objects.create(exp=condition, text='True', seq=0)
        requirement = BooleanExpression.objects.create(label='choose a lunch period')
        seq = 0
        for timeblock in timeblocks:
            ScheduleTestCategory.objects.create(exp=requirement, timeblock=timeblock,
                                                category=self.lunch_category, seq=seq)
            seq += 10
        #   Any one of the blocks will do, so OR the tests together.
        for _ in range(len(timeblocks) - 1):
            BooleanToken.objects.create(exp=requirement, text='OR', seq=seq)
            seq += 10
        return ScheduleConstraint.objects.create(program=self.program, condition=condition,
                                                 requirement=requirement, enforce=enforce,
                                                 autocorrect=autocorrect)

    def decline_lunch(self):
        self.assertTrue(
            self.client.login(username=self.student.username, password='password'),
        )
        dates = self.program.dates()
        post_data = {'day%d-timeslot' % i: -1 for i in range(len(dates))}
        return self.client.post(self.module.get_full_path(), data=post_data)

    def lunch_registration_exists(self):
        return StudentRegistration.valid_objects().filter(
            user=self.student,
            section__parent_class__category=self.lunch_category,
        ).exists()

    def test_declining_lunch_blocked_when_constraint_is_enforced(self):
        """Declining must not sidestep an enforced constraint (issue #1881 follow-up)."""
        self.lunch_section.preregister_student(self.student)
        self.require_lunch(enforce=True)

        self.decline_lunch()
        self.assertTrue(self.lunch_registration_exists(),
                        'Enforced constraint should have prevented the lunch period being dropped')

    def test_declining_lunch_allowed_when_constraint_only_warns(self):
        self.lunch_section.preregister_student(self.student)
        self.require_lunch(enforce=False)

        self.decline_lunch()
        self.assertFalse(self.lunch_registration_exists(),
                         'A warning-only constraint must not block declining lunch')

    def test_declining_lunch_allowed_when_none_was_selected(self):
        """Nothing is newly broken if the student had no lunch to begin with."""
        self.require_lunch(enforce=True)

        response = self.decline_lunch()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.lunch_registration_exists())

    def accept_lunch(self):
        """The generator creates lunch classes accepted; this fixture leaves them unreviewed."""
        from esp.program.class_status import ClassStatus
        self.lunch_class.status = ClassStatus.ACCEPTED
        self.lunch_class.save()
        self.lunch_class.sections.update(status=ClassStatus.ACCEPTED)

    def second_lunch_block(self):
        """A second lunch section an hour after the first."""
        import datetime as dt
        start = dt.datetime.combine(self.lunch_day, dt.time(13, 0))
        event = Event.objects.create(
            program=self.program, event_type=self.lunch_event_type,
            start=start, end=start + dt.timedelta(hours=1),
            short_description='Lunch 13:00', description='Lunch 13:00',
        )
        section = ClassSection.objects.create(
            parent_class=self.lunch_class, duration='1.0', max_class_capacity=100)
        section.meeting_times.add(event)
        return event, section

    def test_autocorrect_enrols_the_student_in_a_free_lunch_block(self):
        self.accept_lunch()
        self.require_lunch(enforce=True, autocorrect=True)
        self.assertFalse(self.lunch_registration_exists())

        added = autocorrect_schedule(self.student, self.program)

        self.assertEqual([section.id for section in added], [self.lunch_section.id])
        self.assertTrue(self.lunch_registration_exists())

    def test_autocorrect_does_nothing_when_no_lunch_block_is_free(self):
        """Nothing to repair once the student's lunch blocks are all occupied."""
        self.accept_lunch()
        self.require_lunch(enforce=True, autocorrect=True)
        busy = self.program.sections().exclude(parent_class=self.lunch_class).first()
        if busy is None:
            self.skipTest('Program has no non-lunch section')
        busy.meeting_times.set([self.lunch_event])
        busy.preregister_student(self.student)

        self.assertEqual(autocorrect_schedule(self.student, self.program), [])
        self.assertFalse(self.lunch_registration_exists())

    def test_autocorrect_is_off_unless_the_constraint_asks_for_it(self):
        self.accept_lunch()
        self.require_lunch(enforce=True, autocorrect=False)
        self.assertEqual(autocorrect_schedule(self.student, self.program), [])

    def test_add_is_refused_only_when_it_uses_up_the_last_lunch_block(self):
        """The #822 exception case: an already-overbooked student stays free."""
        second_event, _second_lunch = self.second_lunch_block()
        self.accept_lunch()
        self.require_lunch(enforce=True, timeblocks=[self.lunch_event, second_event])

        sections = list(self.program.sections().exclude(parent_class=self.lunch_class))
        if len(sections) < 2:
            self.skipTest('Program needs two non-lunch sections')
        first, second = sections[0], sections[1]
        first.meeting_times.set([self.lunch_event])
        second.meeting_times.set([second_event])

        #   One lunch block still free, so this is repairable and allowed.
        self.assertEqual(
            unrepairable_requirements(self.student, self.program, add_sections=[first]), [])
        first.preregister_student(self.student)

        #   This one would take the last block, so it is refused.
        self.assertTrue(
            unrepairable_requirements(self.student, self.program, add_sections=[second]))

        #   Once an admin has overbooked them anyway, they are not stuck.
        second.preregister_student(self.student)
        other = self.program.sections().exclude(
            parent_class=self.lunch_class).exclude(id__in=[first.id, second.id]).first()
        if other is not None:
            self.assertEqual(
                unrepairable_requirements(self.student, self.program, add_sections=[other]), [])
