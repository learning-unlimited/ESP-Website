from __future__ import absolute_import
import random

from django.db.models import Q

from esp.program.models import ClassSection, StudentRegistration
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

        log = BatchClassRegModule.batch_register(
            filterObj, section, override_full=True
        )
        self.assertIn('succeeded', log)
        self.assertIn('Summary', log)

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

        log = BatchClassRegModule.batch_register(
            filterObj, section, override_full=True
        )
        self.assertIn('[SKIP]', log)
        self.assertIn('0 succeeded', log)
        self.assertIn('1 skipped', log)
