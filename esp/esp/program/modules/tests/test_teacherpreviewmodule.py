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

from types import SimpleNamespace

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.middleware.esperrormiddleware import ESPError_NoLog
from esp.resources.models import ResourceType, Resource, ResourceAssignment

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
        kwargs.update({'num_students': 3, 'num_teachers': 3})
        super().setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # Get the TeacherPreviewModule instance
        pm = ProgramModule.objects.get(handler='TeacherPreviewModule', module_type='teach')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)

        # Ensure exactly one printables module object exists for this program.
        ProgramModuleObj.objects.filter(
            program=self.program,
            module__handler__icontains='printables'
        ).delete()
        pm_printables = ProgramModule.objects.get(handler='ProgramPrintables', module_type='manage')
        ProgramModuleObj.getFromProgModule(self.program, pm_printables)

        # Use a fixed teacher index for determinism across test runs.
        self.teacher = self.teachers[0]
        self.teacher_classes = self.teacher.getTaughtClassesFromProgram(self.program)
        self.teacher_sections = self.teacher.getTaughtSectionsFromProgram(self.program)

    def _assign_resources_to_classes(self, classes):
        """Ensure every section in `classes` has at least one ResourceAssignment.

        schedule_randomly() assigns rooms where viable; this helper fills in any
        sections that were skipped (e.g. no viable room found at the time).
        """
        classroom_type = ResourceType.objects.filter(name='Classroom').first()
        room_counter = 0
        for cls in classes:
            for section in cls.sections.all():
                if section.resourceassignment_set.exists():
                    continue
                for timeslot in section.meeting_times.all():
                    room_counter += 1
                    resource = Resource.objects.create(
                        name='Test Room %d' % room_counter,
                        res_type=classroom_type,
                        event=timeslot,
                        num_students=50,
                    )
                    ResourceAssignment.objects.create(
                        resource=resource,
                        target=section,
                    )

    def _get_schedule_response(self, user, endpoint, query_params=None):
        """Request a schedule endpoint through Django's test client."""
        self.assertTrue(
            self.client.login(username=user.username, password='password'),
            'Could not log in test user %s' % user.username
        )
        response = self.client.get(
            '/teach/%s/%s' % (self.program.getUrlBase(), endpoint),
            query_params or {}
        )
        self.client.logout()
        return response

    def test_teacher_schedule_generation_with_printables_module(self):
        """
        Test that teacher schedule is generated correctly when a printables module exists.
        Acceptance: Teacher schedule context contains expected class data
        """
        pmos = ProgramModuleObj.objects.filter(program=self.program, module__handler='ProgramPrintables')
        self.assertEqual(pmos.count(), 1, 'Expected one ProgramPrintables module for this program')

        self._assign_resources_to_classes(self.teacher_classes)
        scheduled_sections = [
            sec for sec in self.teacher_sections
            if sec.meeting_times.all().exists()
            and sec.resourceassignment_set.all().exists()
            and sec.status > 0
        ]

        response = self._get_schedule_response(self.teacher, 'teacherschedule')

        self.assertEqual(response.status_code, 200)
        self.assertIn('scheditems', response.context)
        scheditems = response.context['scheditems']

        self.assertEqual(
            len(scheditems),
            len(scheduled_sections),
            'Expected %d schedule items, got %d' % (len(scheduled_sections), len(scheditems))
        )

        for item in scheditems:
            self.assertIn('name', item)
            self.assertIn('teacher', item)
            self.assertIn('cls', item)
            self.assertEqual(item['teacher'], self.teacher)
            self.assertEqual(item['name'], self.teacher.name())

        self.assertTrue(response.context['teachers'])
        self.assertFalse(response.context['moderators'])

    def test_moderator_inclusive_schedule_generation(self):
        """
        Test that moderator-inclusive schedule includes both taught and moderated classes.
        Acceptance: Schedule contains correct role assignments (Teacher vs Moderator)
        """
        self._assign_resources_to_classes(self.teacher_classes)

        taught_class = self.teacher_classes[0]
        moderated_class = self.teacher_classes[1] if len(self.teacher_classes) > 1 else taught_class

        if taught_class != moderated_class:
            moderated_class.removeTeacher(self.teacher)
            moderator_section = moderated_class.sections.all()[0]
            moderator_section.moderators.add(self.teacher)
            moderator_section.save()

        response = self._get_schedule_response(self.teacher, 'teachermoderatorschedule')

        self.assertEqual(response.status_code, 200)
        self.assertIn('scheditems', response.context)
        scheditems = response.context['scheditems']

        for item in scheditems:
            self.assertIn('role', item)
            self.assertIn(item['role'], ['Teacher', self.program.getModeratorTitle()])

        self.assertTrue(response.context['teachers'])
        self.assertTrue(response.context['moderators'])

    def test_admin_impersonation_via_user_query_param(self):
        """
        Test that admin can impersonate another teacher via ?user= query parameter.
        Acceptance: Admin receives schedule for impersonated user, not own schedule
        """
        admin_user = self.admins[0]
        impersonate_teacher = self.teachers[0]

        impersonate_classes = impersonate_teacher.getTaughtClassesFromProgram(self.program)
        self._assign_resources_to_classes(impersonate_classes)

        response = self._get_schedule_response(
            admin_user,
            'teacherschedule',
            query_params={'user': str(impersonate_teacher.id)}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('scheditems', response.context)
        scheditems = response.context['scheditems']

        for item in scheditems:
            self.assertEqual(item['teacher'], impersonate_teacher)
            self.assertEqual(item['name'], impersonate_teacher.name())

    def test_admin_cannot_impersonate_without_user_param(self):
        """
        Test that admin receives their own schedule when ?user= is omitted.
        """
        admin_user = self.admins[0]
        response = self._get_schedule_response(admin_user, 'teacherschedule')

        self.assertEqual(response.status_code, 200)

        # Admin does not teach classes in ProgramFrameworkTest setup; schedule should be empty.
        scheditems = response.context['scheditems']
        self.assertEqual(len(scheditems), 0)

    def test_non_admin_cannot_impersonate_other_teacher(self):
        """
        Test that non-admin teachers cannot impersonate another teacher via query param.
        """
        teacher1 = self.teachers[0]
        teacher2 = self.teachers[1]

        self._assign_resources_to_classes(teacher1.getTaughtClassesFromProgram(self.program))
        self._assign_resources_to_classes(teacher2.getTaughtClassesFromProgram(self.program))

        response = self._get_schedule_response(
            teacher1,
            'teacherschedule',
            query_params={'user': str(teacher2.id)}
        )

        scheditems = response.context['scheditems']
        for item in scheditems:
            self.assertEqual(item['teacher'], teacher1)

    def test_error_when_no_printables_module_resolved(self):
        """
        Test that ESPError is raised when no printables module can be resolved.
        Acceptance: ESPError with appropriate message is raised
        """
        ProgramModuleObj.objects.filter(
            program=self.program,
            module__handler__icontains='printables'
        ).delete()

        request = SimpleNamespace(
            user=self.teacher,
            GET={},
            build_absolute_uri=lambda: '/teach/%s/teacherschedule' % self.program.getUrlBase(),
        )

        with self.assertRaises(ESPError_NoLog) as ctx:
            self.moduleobj.teacherhandout(
                request,
                'teach',
                None,
                None,
                self.moduleobj,
                None,
                self.program,
                template_file='teacherschedule.html'
            )

        self.assertIn('No printables module resolved', str(ctx.exception))

    def test_error_when_multiple_printables_modules_exist(self):
        """
        Test that ESPError is raised when multiple printables modules exist (ambiguous).
        """
        second_printables_module = ProgramModule.objects.create(
            link_title='Extra Printables',
            admin_title='Extra Printables',
            inline_template='',
            module_type='manage',
            handler='ProgramPrintablesExtra',
            seq=9999,
            required=False,
            choosable=0,
        )
        test_pmo = ProgramModuleObj.objects.create(
            program=self.program,
            module=second_printables_module,
            seq=9999,
            required=False,
            required_label='',
            link_title='',
        )

        request = SimpleNamespace(
            user=self.teacher,
            GET={},
            build_absolute_uri=lambda: '/teach/%s/teacherschedule' % self.program.getUrlBase(),
        )

        try:
            with self.assertRaises(ESPError_NoLog):
                self.moduleobj.teacherhandout(
                    request,
                    'teach',
                    None,
                    None,
                    self.moduleobj,
                    None,
                    self.program,
                    template_file='teacherschedule.html'
                )
        finally:
            test_pmo.delete()
            second_printables_module.delete()

    def test_filters_out_unscheduled_classes(self):
        """
        Test that classes without meeting times are filtered out.
        Acceptance: Schedule does not include classes without meeting_times
        """
        self._assign_resources_to_classes(self.teacher_classes)

        unscheduled_section = self.teacher.getTaughtSectionsFromProgram(self.program)[0]
        unscheduled_section.meeting_times.clear()
        self.assertEqual(unscheduled_section.meeting_times.count(), 0)

        response = self._get_schedule_response(self.teacher, 'teacherschedule')

        schedule_class_ids = [item['cls'].id for item in response.context['scheditems']]
        self.assertNotIn(
            unscheduled_section.id,
            schedule_class_ids,
            'Unscheduled class should be filtered out'
        )

    def test_filters_out_classes_without_resource_assignments(self):
        """
        Test that classes without resource assignments are filtered out.
        Acceptance: Schedule does not include classes without resourceassignment_set
        """
        for cls in self.teacher_classes:
            for section in cls.sections.all():
                section.resourceassignment_set.all().delete()

        response = self._get_schedule_response(self.teacher, 'teacherschedule')

        self.assertEqual(
            len(response.context['scheditems']),
            0,
            'Classes without resource assignments should be filtered out'
        )

    def test_filters_out_inactive_classes(self):
        """
        Test that classes with status <= 0 are filtered out.
        Acceptance: Schedule does not include classes with inactive status
        """
        self._assign_resources_to_classes(self.teacher_classes)

        inactive_section = self.teacher.getTaughtSectionsFromProgram(self.program)[0]
        inactive_section.status = -1
        inactive_section.save()

        response = self._get_schedule_response(self.teacher, 'teacherschedule')

        schedule_class_ids = [item['cls'].id for item in response.context['scheditems']]
        self.assertNotIn(
            inactive_section.id,
            schedule_class_ids,
            'Inactive class should be filtered out'
        )

    def test_schedule_items_sorted_by_class(self):
        """
        Test that schedule items are returned in sorted order.
        Acceptance: Schedule items maintain sorted order by _sort_key()
        """
        self._assign_resources_to_classes(self.teacher_classes)

        response = self._get_schedule_response(self.teacher, 'teacherschedule')

        scheditems = response.context['scheditems']

        if len(scheditems) > 1:
            returned_class_ids = [item['cls'].id for item in scheditems]

            # Mirror the source's sort: key=lambda s: s._sort_key()
            valid_sections = sorted(
                [
                    sec for sec in self.teacher.getTaughtSectionsFromProgram(self.program)
                    if sec.meeting_times.all().exists()
                    and sec.resourceassignment_set.all().exists()
                    and sec.status > 0
                ],
                key=lambda s: s._sort_key()
            )
            expected_class_ids = [sec.id for sec in valid_sections]

            self.assertEqual(returned_class_ids, expected_class_ids)

    def test_moderator_schedule_filters_correctly(self):
        """
        Test that moderator schedule applies the same filtering rules.
        Acceptance: Moderator schedule filters unscheduled/inactive/no-resource classes
        """
        self._assign_resources_to_classes(self.teacher_classes)

        for cls in self.teacher_classes:
            for section in cls.sections.all():
                section.moderators.clear()
                section.moderators.add(self.teacher)
                section.save()
            cls.removeTeacher(self.teacher)

        response = self._get_schedule_response(self.teacher, 'teachermoderatorschedule')

        for item in response.context['scheditems']:
            cls = item['cls']
            self.assertTrue(cls.meeting_times.all().exists(), 'Class has meeting times')
            self.assertTrue(cls.resourceassignment_set.all().exists(), 'Class has resources')
            self.assertGreater(cls.status, 0, 'Class is active')

    def test_moderator_only_schedule(self):
        """
        Test that moderator-only schedule (no taught classes) shows only moderated classes.
        """
        self._assign_resources_to_classes(self.teacher_classes)

        for cls in self.teacher_classes:
            cls.removeTeacher(self.teacher)

        for cls in self.teacher_classes:
            for section in cls.sections.all():
                section.moderators.add(self.teacher)
                section.save()

        response = self._get_schedule_response(self.teacher, 'moderatorschedule')

        scheditems = response.context['scheditems']
        self.assertGreater(len(scheditems), 0)
        self.assertFalse(response.context['teachers'])
        self.assertTrue(response.context['moderators'])

        for item in scheditems:
            self.assertIn('cls', item)
            self.assertIn('teacher', item)

    def test_schedule_context_has_required_fields(self):
        """
        Test that schedule response context has all required fields with correct types.
        """
        self._assign_resources_to_classes(self.teacher_classes)

        response = self._get_schedule_response(self.teacher, 'teacherschedule')

        self.assertIn('module', response.context)
        self.assertIn('scheditems', response.context)
        self.assertIn('teachers', response.context)
        self.assertIn('moderators', response.context)

        self.assertEqual(response.context['module'], self.moduleobj)
        self.assertIsInstance(response.context['scheditems'], list)
        self.assertIsInstance(response.context['teachers'], bool)
        self.assertIsInstance(response.context['moderators'], bool)
