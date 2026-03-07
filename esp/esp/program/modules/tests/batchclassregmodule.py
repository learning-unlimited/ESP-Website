from __future__ import absolute_import
from unittest.mock import patch

from django.db.models import Q

from esp.program.models import ClassSection
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, PersistentQueryFilter


class BatchClassRegModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_students': 10, 'num_teachers': 3, 'classes_per_teacher': 1,
            'sections_per_class': 1, 'num_rooms': 3,
        })
        super(BatchClassRegModuleTest, self).setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()

        pm = ProgramModule.objects.get(handler='BatchClassRegModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

        self.admin, created = ESPUser.objects.get_or_create(username='admin')
        self.admin.set_password('password')
        self.admin.makeAdmin()

    def test_main_page_loads(self):
        self.client.login(username='admin', password='password')
        r = self.client.get('/manage/' + self.program.url + '/batchclassreg')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Batch Class Registration')

    def test_batch_register(self):
        from esp.program.modules.handlers.batchclassregmodule import BatchClassRegModule

        section = ClassSection.objects.filter(
            parent_class__parent_program=self.program,
            status__gte=10
        ).first()
        if section is None:
            self.skipTest("No accepted sections in test program")

        students = self.students[:3]
        q = Q(id__in=[s.id for s in students])
        filterObj = PersistentQueryFilter.create_from_Q(ESPUser, q)
        filterObj.save()

        result = BatchClassRegModule.batch_register(
            filterObj, section, override_full=True
        )
        self.assertGreater(result['success_count'], 0)
        self.assertEqual(result['total'], 3)

    def test_batch_register_skip_already_enrolled(self):
        from esp.program.modules.handlers.batchclassregmodule import BatchClassRegModule

        section = ClassSection.objects.filter(
            parent_class__parent_program=self.program,
            status__gte=10
        ).first()
        if section is None:
            self.skipTest("No accepted sections in test program")

        student = self.students[0]
        section.preregister_student(student, overridefull=True)

        q = Q(id=student.id)
        filterObj = PersistentQueryFilter.create_from_Q(ESPUser, q)
        filterObj.save()

        result = BatchClassRegModule.batch_register(
            filterObj, section, override_full=True
        )
        self.assertEqual(result['success_count'], 0)
        self.assertEqual(result['skip_count'], 1)
        self.assertEqual(result['results'][0]['status'], 'skip')

    def test_batch_register_time_conflict(self):
        """A student enrolled in a conflicting timeslot gets 'conflict' status."""
        from esp.program.modules.handlers.batchclassregmodule import BatchClassRegModule

        sections = list(ClassSection.objects.filter(
            parent_class__parent_program=self.program,
            status__gte=10
        )[:2])
        if len(sections) < 2:
            self.skipTest("Need at least 2 accepted sections")

        section_a, section_b = sections
        # Ensure they share a timeslot so we get a conflict
        times_a = set(section_a.meeting_times.values_list('id', flat=True))
        times_b = set(section_b.meeting_times.values_list('id', flat=True))
        if not times_a & times_b:
            # Force overlap by assigning same timeslot
            ts = section_a.meeting_times.first()
            if ts:
                section_b.meeting_times.add(ts)
            else:
                self.skipTest("No timeslots available for conflict test")

        student = self.students[0]
        section_a.preregister_student(student, overridefull=True)

        q = Q(id=student.id)
        filterObj = PersistentQueryFilter.create_from_Q(ESPUser, q)
        filterObj.save()

        result = BatchClassRegModule.batch_register(
            filterObj, section_b, override_full=True
        )
        self.assertEqual(result['fail_count'], 1)
        self.assertEqual(result['results'][0]['status'], 'conflict')

    def test_batch_register_full_section(self):
        """When section is full and override_full=False, student gets 'full' status."""
        from esp.program.modules.handlers.batchclassregmodule import BatchClassRegModule

        section = ClassSection.objects.filter(
            parent_class__parent_program=self.program,
            status__gte=10
        ).first()
        if section is None:
            self.skipTest("No accepted sections in test program")

        student = self.students[0]
        q = Q(id=student.id)
        filterObj = PersistentQueryFilter.create_from_Q(ESPUser, q)
        filterObj.save()

        with patch.object(type(section), 'isFull', return_value=True):
            result = BatchClassRegModule.batch_register(
                filterObj, section, override_full=False
            )
        self.assertEqual(result['fail_count'], 1)
        self.assertEqual(result['results'][0]['status'], 'full')
