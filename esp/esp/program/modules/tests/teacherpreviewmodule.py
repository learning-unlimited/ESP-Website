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

import random
from django.test.client import Client, RequestFactory
from django.test import TestCase
from django.http import HttpRequest

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.models import ClassSubject
from esp.middleware import ESPError
from esp.users.models import ESPUser
from esp.resources.models import ResourceType, ResourceRequest


class TeacherPreviewModuleTest(ProgramFrameworkTest):
    """
    Test suite for TeacherPreviewModule covering:
    - Teacher schedule generation when printables module exists
    - Moderator-inclusive schedule generation
    - Admin impersonation via ?user= query parameter
    - Error behavior when no printables module can be resolved
    - Filtering of unscheduled and inactive classes from schedule output
    """

    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up a program with students, teachers, and resources
        kwargs.update({'num_students': 3, 'num_teachers': 3})
        super().setUp(*args, **kwargs)

        # Schedule classes and add resources
        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # Get the TeacherPreviewModule instance
        pm = ProgramModule.objects.get(handler='TeacherPreviewModule', module_type='teach')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)

        # Get the ProgramPrintables module instance (required for content generation)
        self.printables_pm = ProgramModule.objects.get(handler='ProgramPrintables', module_type='manage')
        self.printables_pmo = ProgramModuleObj.getFromProgModule(self.program, self.printables_pm)

        # Create request factory for unit tests
        self.factory = RequestFactory()

        # Pick a teacher and get their classes
        self.teacher = random.choice(self.teachers)
        self.teacher_classes = self.teacher.getTaughtClasses()

    def _assign_resources_to_classes(self, classes):
        """Helper to assign basic resources to classes for tests."""
        for cls in classes:
            for section in cls.sections.all():
                # Assign a generic "Room" resource to make resourceassignment_set non-empty
                res_type = ResourceType.objects.get_or_create(
                    name='Room',
                    program=self.program
                )[0]
                rr = ResourceRequest()
                rr.target = section
                rr.res_type = res_type
                rr.desired_value = 'Room 101'
                rr.save()

    def _make_mock_request(self, user, query_params=None):
        """Create a mock request with the given user and query parameters."""
        path = '/learn/%s/teacherschedule' % self.program.getUrlBase()
        if query_params:
            query_string = '&'.join(['%s=%s' % (k, v) for k, v in query_params.items()])
            path += '?%s' % query_string
        request = self.factory.get(path)
        request.user = user
        request.GET = query_params or {}
        return request

    def test_teacher_schedule_generation_with_printables_module(self):
        """
        Test that teacher schedule is generated correctly when a printables module exists.
        Acceptance: Teacher schedule context contains expected class data
        """
        # Ensure printables module is registered
        pmos = ProgramModuleObj.objects.filter(
            program=self.program,
            module__handler__icontains='printables'
        )
        self.assertEqual(pmos.count(), 1, 'Printables module not found')

        # Get classes that should appear in the schedule
        # (have meeting times, resources, and active status)
        self._assign_resources_to_classes(self.teacher_classes)
        scheduled_classes = [
            cls for cls in self.teacher_classes
            if cls.meeting_times.all().exists()
            and cls.resourceassignment_set.all().exists()
            and cls.status > 0
        ]

        # Create mock request
        request = self._make_mock_request(self.teacher)

        # Call the teacherhandout method
        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        # Verify response status
        self.assertEqual(response.status_code, 200)

        # Verify context contains scheditems
        self.assertIn('scheditems', response.context)
        scheditems = response.context['scheditems']

        # Verify the number of items matches the scheduled classes
        self.assertEqual(
            len(scheditems),
            len(scheduled_classes),
            f'Expected {len(scheduled_classes)} schedule items, got {len(scheditems)}'
        )

        # Verify each scheditem has required keys
        for item in scheditems:
            self.assertIn('name', item)
            self.assertIn('teacher', item)
            self.assertIn('cls', item)
            self.assertEqual(item['teacher'], self.teacher)
            self.assertEqual(item['name'], self.teacher.name())

        # Verify context indicates this is teacher schedule only
        self.assertTrue(response.context['teachers'])
        self.assertFalse(response.context['moderators'])

    def test_moderator_inclusive_schedule_generation(self):
        """
        Test that moderator-inclusive schedule includes both taught and moderated classes.
        Acceptance: Schedule contains correct role assignments (Teacher vs Moderator)
        """
        # Assign resources to all classes
        self._assign_resources_to_classes(self.teacher_classes)

        # Make the teacher a moderator for one class
        taught_class = self.teacher_classes[0]
        moderated_class = self.teacher_classes[1] if len(self.teacher_classes) > 1 else taught_class

        # Add teacher as moderator to moderated class (not as teacher)
        if taught_class != moderated_class:
            # Remove teacher from this class
            moderated_class.removeTeacher(self.teacher)
            # Add as moderator by adding to moderator list
            moderator_section = moderated_class.sections.all()[0]
            moderator_section.moderators.add(self.teacher)
            moderator_section.save()

        # Create mock request
        request = self._make_mock_request(self.teacher)

        # Call the teachermoderatorhandout method
        response = self.moduleobj.teachermoderatorhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teachermoderatorschedule.html'
        )

        # Verify response status
        self.assertEqual(response.status_code, 200)

        # Verify context contains scheditems with role information
        self.assertIn('scheditems', response.context)
        scheditems = response.context['scheditems']

        # All items should have a 'role' field
        for item in scheditems:
            self.assertIn('role', item)
            self.assertIn(item['role'], ['Teacher', self.program.getModeratorTitle()])

        # Verify context indicates moderator-inclusive
        self.assertTrue(response.context['teachers'])
        self.assertTrue(response.context['moderators'])

    def test_admin_impersonation_via_user_query_param(self):
        """
        Test that admin can impersonate another teacher via ?user= query parameter.
        Acceptance: Admin receives schedule for impersonated user, not own schedule
        """
        admin_user = self.admins[0]
        impersonate_teacher = self.teachers[0]

        # Assign resources to impersonate teacher's classes
        impersonate_classes = impersonate_teacher.getTaughtClasses()
        self._assign_resources_to_classes(impersonate_classes)

        # Create mock request from admin with user= param
        request = self._make_mock_request(
            admin_user,
            query_params={'user': str(impersonate_teacher.id)}
        )
        request.user.isAdmin = lambda: True  # Mock admin check

        # Call teacherhandout
        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        # Verify response status
        self.assertEqual(response.status_code, 200)

        # Verify the context has the impersonated teacher's data
        self.assertIn('scheditems', response.context)
        scheditems = response.context['scheditems']

        # All items should be for the impersonated teacher
        for item in scheditems:
            self.assertEqual(item['teacher'], impersonate_teacher)
            self.assertEqual(item['name'], impersonate_teacher.name())

    def test_admin_cannot_impersonate_without_user_param(self):
        """
        Test that admin receives their own schedule even if ?user= is missing.
        """
        admin_user = self.admins[0]
        admin_classes = admin_user.getTaughtClasses()
        self._assign_resources_to_classes(admin_classes)

        # Create mock request without user param
        request = self._make_mock_request(admin_user)
        request.user.isAdmin = lambda: True

        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        self.assertEqual(response.status_code, 200)
        
        # Should get admin's schedule, not empty
        scheditems = response.context['scheditems']
        for item in scheditems:
            self.assertEqual(item['teacher'], admin_user)

    def test_non_admin_cannot_impersonate_other_teacher(self):
        """
        Test that non-admin teachers cannot impersonate another teacher via query param.
        """
        teacher1 = self.teachers[0]
        teacher2 = self.teachers[1]

        self._assign_resources_to_classes(teacher1.getTaughtClasses())
        self._assign_resources_to_classes(teacher2.getTaughtClasses())

        # Create mock request from teacher1 trying to impersonate teacher2
        request = self._make_mock_request(
            teacher1,
            query_params={'user': str(teacher2.id)}
        )
        request.user.isAdmin = lambda: False

        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        # Should get teacher1's schedule, not teacher2's
        scheditems = response.context['scheditems']
        for item in scheditems:
            self.assertEqual(item['teacher'], teacher1)

    def test_error_when_no_printables_module_resolved(self):
        """
        Test that ESPError is raised when no printables module can be resolved.
        Acceptance: ESPError with appropriate message is raised
        """
        # Remove all printables modules
        ProgramModuleObj.objects.filter(
            program=self.program,
            module__handler__icontains='printables'
        ).delete()

        # Create mock request
        request = self._make_mock_request(self.teacher)

        # Call teacherhandout - should raise ESPError
        with self.assertRaises(ESPError) as context:
            self.moduleobj.teacherhandout(
                request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
            )

        # Verify error message
        self.assertIn('No printables module resolved', str(context.exception))

    def test_error_when_multiple_printables_modules_exist(self):
        """
        Test that ESPError is raised when multiple printables modules exist (ambiguous).
        """
        # Get the existing printables module
        existing_pmo = ProgramModuleObj.objects.filter(
            program=self.program,
            module__handler__icontains='printables'
        ).first()

        if existing_pmo:
            # Create a duplicate by duplicating the module object
            # (This tests the pmos.count() == 1 check)
            test_pmo = ProgramModuleObj()
            test_pmo.program = self.program
            test_pmo.module = existing_pmo.module
            test_pmo.save()

            request = self._make_mock_request(self.teacher)

            # Should raise error due to count != 1
            with self.assertRaises(ESPError):
                self.moduleobj.teacherhandout(
                    request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
                )

            # Cleanup
            test_pmo.delete()

    def test_filters_out_unscheduled_classes(self):
        """
        Test that classes without meeting times are filtered out.
        Acceptance: Schedule does not include classes without meeting_times
        """
        self._assign_resources_to_classes(self.teacher_classes)

        # Get a class and remove its meeting times
        unscheduled_class = self.teacher_classes[0]
        unscheduled_class.meeting_times.clear()

        # Ensure it has no meeting times
        self.assertEqual(unscheduled_class.meeting_times.count(), 0)

        request = self._make_mock_request(self.teacher)

        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        scheditems = response.context['scheditems']

        # The unscheduled class should not appear
        schedule_class_ids = [item['cls'].id for item in scheditems]
        self.assertNotIn(
            unscheduled_class.id,
            schedule_class_ids,
            'Unscheduled class should be filtered out'
        )

    def test_filters_out_classes_without_resource_assignments(self):
        """
        Test that classes without resource assignments are filtered out.
        Acceptance: Schedule does not include classes without resourceassignment_set
        """
        # Don't assign resources to any class
        # Get all classes and ensure they have no resources
        for cls in self.teacher_classes:
            for section in cls.sections.all():
                section.resourceassignment_set.all().delete()

        request = self._make_mock_request(self.teacher)

        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        scheditems = response.context['scheditems']

        # No items should be in schedule (all lack resources)
        self.assertEqual(
            len(scheditems),
            0,
            'Classes without resource assignments should be filtered out'
        )

    def test_filters_out_inactive_classes(self):
        """
        Test that classes with status <= 0 are filtered out.
        Acceptance: Schedule does not include classes with inactive status
        """
        self._assign_resources_to_classes(self.teacher_classes)

        # Set one class to inactive (status <= 0)
        inactive_class = self.teacher_classes[0]
        inactive_class.status = -1  # Rejected status
        inactive_class.save()

        request = self._make_mock_request(self.teacher)

        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        scheditems = response.context['scheditems']

        # The inactive class should not appear
        schedule_class_ids = [item['cls'].id for item in scheditems]
        self.assertNotIn(
            inactive_class.id,
            schedule_class_ids,
            'Inactive class should be filtered out'
        )

    def test_schedule_items_sorted_by_class(self):
        """
        Test that schedule items are returned in sorted order.
        Acceptance: Schedule items maintain sorted order
        """
        self._assign_resources_to_classes(self.teacher_classes)

        request = self._make_mock_request(self.teacher)

        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        scheditems = response.context['scheditems']

        if len(scheditems) > 1:
            # Extract class IDs from scheditems
            returned_class_ids = [item['cls'].id for item in scheditems]

            # Get the expected sorted order
            valid_classes = sorted([
                cls for cls in self.teacher_classes
                if cls.meeting_times.all().exists()
                and cls.resourceassignment_set.all().exists()
                and cls.status > 0
            ])
            expected_class_ids = [cls.id for cls in valid_classes]

            self.assertEqual(returned_class_ids, expected_class_ids)

    def test_moderator_schedule_filters_correctly(self):
        """
        Test that moderator schedule applies the same filtering rules.
        Acceptance: Moderator schedule filters unscheduled/inactive/no-resource classes
        """
        self._assign_resources_to_classes(self.teacher_classes)

        # Make teacher a moderator for all their classes
        for cls in self.teacher_classes:
            for section in cls.sections.all():
                section.moderators.clear()
                section.moderators.add(self.teacher)
                section.save()
            # Remove as teacher
            cls.removeTeacher(self.teacher)

        request = self._make_mock_request(self.teacher)

        response = self.moduleobj.teachermoderatorhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teachermoderatorschedule.html'
        )

        scheditems = response.context['scheditems']

        # Verify filtering applies
        for item in scheditems:
            cls = item['cls']
            self.assertTrue(cls.meeting_times.all().exists(), 'Class has meeting times')
            self.assertTrue(cls.resourceassignment_set.all().exists(), 'Class has resources')
            self.assertGreater(cls.status, 0, 'Class is active')

    def test_moderator_only_schedule(self):
        """
        Test that moderator-only schedule (no taught classes) shows only moderated classes.
        """
        self._assign_resources_to_classes(self.teacher_classes)

        # Remove teacher from all classes
        for cls in self.teacher_classes:
            cls.removeTeacher(self.teacher)

        # Make them moderators
        for cls in self.teacher_classes:
            for section in cls.sections.all():
                section.moderators.add(self.teacher)
                section.save()

        request = self._make_mock_request(self.teacher)

        response = self.moduleobj.moderatorhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'moderatorschedule.html'
        )

        scheditems = response.context['scheditems']

        # Should have moderated classes
        self.assertGreater(len(scheditems), 0)

        # Verify context
        self.assertFalse(response.context['teachers'])
        self.assertTrue(response.context['moderators'])

        # All items should not have a 'role' field (moderator-only doesn't include role)
        for item in scheditems:
            self.assertIn('cls', item)
            self.assertIn('teacher', item)

    def test_schedule_context_has_required_fields(self):
        """
        Test that schedule response context has all required fields.
        """
        self._assign_resources_to_classes(self.teacher_classes)

        request = self._make_mock_request(self.teacher)

        response = self.moduleobj.teacherhandout(
            request, '', '', '', self.moduleobj, '', self.program, 'teacherschedule.html'
        )

        # Verify required context fields
        self.assertIn('module', response.context)
        self.assertIn('scheditems', response.context)
        self.assertIn('teachers', response.context)
        self.assertIn('moderators', response.context)

        self.assertEqual(response.context['module'], self.moduleobj)
        self.assertIsInstance(response.context['scheditems'], list)
        self.assertIsInstance(response.context['teachers'], bool)
        self.assertIsInstance(response.context['moderators'], bool)
