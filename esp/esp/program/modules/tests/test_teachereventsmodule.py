__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2024 by the individual contributors
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
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, UserAvailability
from django.contrib.auth.models import Group


class TeacherEventsModuleTest(ProgramFrameworkTest):
    

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3,
            'timeslot_length': 50,
            'timeslot_gap': 10,
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)

        pm = ProgramModule.objects.get(handler='TeacherEventsModule', module_type='teach')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.module.user = self.teachers[0]

        self.training_type = EventType.objects.create(
            description='Teacher Training',
            is_teacher_type=True,
        )

        self.interview_type = EventType.objects.create(
            description='Teacher Interview',
            is_teacher_type=True,
        )

        self.teacher_group, _ = Group.objects.get_or_create(name='Teacher')

        start = datetime.datetime.now() + datetime.timedelta(days=7)
        end   = start + datetime.timedelta(hours=1)
        self.training_event = Event.objects.create(
            program=self.program,
            event_type=self.training_type,
            start=start,
            end=end,
            short_description='Training slot 1',
            description='Training slot 1',
        )

        self.interview_event = Event.objects.create(
            program=self.program,
            event_type=self.interview_type,
            start=start + datetime.timedelta(hours=2),
            end=start + datetime.timedelta(hours=3),
            short_description='Interview slot 1',
            description='Interview slot 1',
        )

        self.teacher  = self.teachers[0]
        self.teacher2 = self.teachers[1]

    def tearDown(self):
        UserAvailability.objects.filter(event__program=self.program).delete()
        Event.objects.filter(program=self.program,
                              event_type__is_teacher_type=True).delete()
        EventType.objects.filter(is_teacher_type=True).delete()
        super().tearDown()


    def test_isStep_true_when_events_exist(self):
        self.assertTrue(self.module.isStep())

    def test_isStep_false_when_no_events(self):
        Event.objects.filter(program=self.program,
                              event_type__is_teacher_type=True).delete()
        self.assertFalse(self.module.isStep())


    def test_getTimes_returns_correct_events(self):
        """getTimes() should return only events matching the given event type."""
        training_times  = self.module.getTimes(self.training_type)
        interview_times = self.module.getTimes(self.interview_type)

        self.assertIn(self.training_event,  training_times)
        self.assertNotIn(self.interview_event, training_times)

        self.assertIn(self.interview_event, interview_times)
        self.assertNotIn(self.training_event, interview_times)

    def test_getTimes_empty_when_no_events_of_type(self):
        """getTimes() should return an empty queryset when no matching events exist."""
        other_type = EventType.objects.create(
            description='Other Type',
            is_teacher_type=True,
        )
        self.assertFalse(self.module.getTimes(other_type).exists())
        other_type.delete()


    def test_teachers_returns_signed_up_teacher(self):
        UserAvailability.objects.create(
            user=self.teacher,
            event=self.training_event,
            role=self.teacher_group,
        )
        teachers_map = self.module.teachers()
        signed_up = teachers_map.get(self.training_type.description)
        self.assertIsNotNone(signed_up)
        self.assertIn(self.teacher, signed_up)

    def test_teachers_excludes_unsigned_teacher(self):
        teachers_map = self.module.teachers()
        for qs in teachers_map.values():
            self.assertNotIn(self.teacher, qs)

    def test_teacherDesc_contains_event_type_description(self):
        desc = self.module.teacherDesc()
        self.assertIn(self.training_type.description, desc)
        self.assertIn(self.interview_type.description, desc)

    def test_entriesByTeacher_empty_before_signup(self):
        entries = self.module.entriesByTeacher(self.teacher)
        for qs in entries.values():
            self.assertFalse(qs.exists())

    def test_entriesByTeacher_populated_after_signup(self):
        UserAvailability.objects.create(
            user=self.teacher,
            event=self.training_event,
            role=self.teacher_group,
        )
        entries = self.module.entriesByTeacher(self.teacher)
        self.assertTrue(entries[self.training_type.description].exists())

    def test_isCompleted_false_before_any_signup(self):
        self.assertFalse(self.module.isCompleted(self.teacher))

    def test_isCompleted_false_when_only_partial_signup(self):
        UserAvailability.objects.create(
            user=self.teacher,
            event=self.training_event,
            role=self.teacher_group,
        )
        self.assertFalse(self.module.isCompleted(self.teacher))

    def test_isCompleted_true_when_all_signed_up(self):
        UserAvailability.objects.create(
            user=self.teacher,
            event=self.training_event,
            role=self.teacher_group,
        )
        UserAvailability.objects.create(
            user=self.teacher,
            event=self.interview_event,
            role=self.teacher_group,
        )
        self.assertTrue(self.module.isCompleted(self.teacher))

    def test_isCompleted_true_when_no_events_exist(self):
        Event.objects.filter(program=self.program,
                              event_type__is_teacher_type=True).delete()
        self.assertTrue(self.module.isCompleted(self.teacher))


    def test_event_signup_get_renders_for_eligible_teacher(self):
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Couldn't log in as teacher %s" % self.teacher.username,
        )
        response = self.client.get(self.module.get_full_path())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'form', response.content.lower())

    def test_event_signup_get_blocked_for_anonymous_user(self):
        self.client.logout()
        response = self.client.get(self.module.get_full_path())
        self.assertNotEqual(response.status_code, 200)

    def test_event_signup_get_blocked_for_student(self):
        student = self.students[0]
        self.assertTrue(
            self.client.login(username=student.username, password='password'),
            "Couldn't log in as student %s" % student.username,
        )
        response = self.client.get(self.module.get_full_path())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'event_type_', response.content)

    def test_event_signup_post_creates_useravailability(self):
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Couldn't log in as teacher %s" % self.teacher.username,
        )
        post_data = {
            'event_type_%d' % self.training_type.id:  self.training_event.id,
            'event_type_%d' % self.interview_type.id: self.interview_event.id,
        }
        response = self.client.post(self.module.get_full_path(), data=post_data)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            UserAvailability.objects.filter(
                user=self.teacher, event=self.training_event,
            ).exists(),
            "Expected UserAvailability for training event after POST",
        )
        self.assertTrue(
            UserAvailability.objects.filter(
                user=self.teacher, event=self.interview_event,
            ).exists(),
            "Expected UserAvailability for interview event after POST",
        )

    def test_event_signup_post_replaces_previous_selection(self):
        start2 = datetime.datetime.now() + datetime.timedelta(days=8)
        training_event_2 = Event.objects.create(
            program=self.program,
            event_type=self.training_type,
            start=start2,
            end=start2 + datetime.timedelta(hours=1),
            short_description='Training slot 2',
            description='Training slot 2',
        )

        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
        )

        
        self.client.post(self.module.get_full_path(), data={
            'event_type_%d' % self.training_type.id:  self.training_event.id,
            'event_type_%d' % self.interview_type.id: '',
        })
        self.assertTrue(
            UserAvailability.objects.filter(
                user=self.teacher, event=self.training_event,
            ).exists()
        )

        
        self.client.post(self.module.get_full_path(), data={
            'event_type_%d' % self.training_type.id:  training_event_2.id,
            'event_type_%d' % self.interview_type.id: '',
        })
        self.assertFalse(
            UserAvailability.objects.filter(
                user=self.teacher, event=self.training_event,
            ).exists(),
            "Old training signup should have been removed on re-signup",
        )
        self.assertTrue(
            UserAvailability.objects.filter(
                user=self.teacher, event=training_event_2,
            ).exists(),
            "New training signup should exist after re-signup",
        )

        training_event_2.delete()

    def test_event_signup_post_with_no_selection_clears_entries(self):
       
        UserAvailability.objects.create(
            user=self.teacher,
            event=self.training_event,
            role=self.teacher_group,
        )

        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
        )
        
        post_data = {
            'event_type_%d' % self.training_type.id:  '',
            'event_type_%d' % self.interview_type.id: '',
        }
        response = self.client.post(self.module.get_full_path(), data=post_data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            UserAvailability.objects.filter(
                user=self.teacher,
                event__event_type__in=[self.training_type, self.interview_type],
            ).exists(),
            "All event availabilities should be cleared after submitting empty form",
        )

    

    def test_event_signup_get_prepopulates_existing_selection(self):
        UserAvailability.objects.create(
            user=self.teacher,
            event=self.training_event,
            role=self.teacher_group,
        )
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
        )
        response = self.client.get(self.module.get_full_path())
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            str(self.training_event.id).encode(),
            response.content,
            "Expected pre-populated training event id in GET response",
        )
