import datetime

from django.test import RequestFactory
from django.utils import timezone
from django.core.cache import cache

from esp.program.models import ClassSubject, ClassSection
from esp.program.modules.handlers.teacherbigboardmodule import TeacherBigBoardModule, get_filter
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class TeacherBigBoardModuleTests(ProgramFrameworkTest):
    # tests for teacher dashboard metrics and rendering

    def setUp(self):
        super().setUp(
            num_timeslots=2,
            num_teachers=2,
            classes_per_teacher=2,
            sections_per_class=1,
            num_rooms=2,
            num_students=0,
        )
        self.factory = RequestFactory()
        self.admin = self.admins[0]
        self.module = TeacherBigBoardModule()

        # wipe cache so tests don't bleed into each other
        self._flush_cache()

        self.schedule_randomly()

        # hardcode timestamps so tests are predictable
        for cls in self.program.classes():
            cls.timestamp = timezone.now() - datetime.timedelta(days=1)
            cls.save()

        # set up mock data for class 0 (approved and scheduled with teacher 0)
        self.cls0 = self.program.classes()[0]
        self.cls0.teachers.set([self.teachers[0]])
        self.cls0.status = 1
        self.cls0.save()
        sec0 = self.cls0.sections.first()
        sec0.status = 1
        sec0.duration = 1
        sec0.save()

        # class 1 is approved but not scheduled yet
        self.cls1 = self.program.classes()[1]
        self.cls1.teachers.set([self.teachers[0]])
        self.cls1.status = 1
        self.cls1.save()
        sec1 = self.cls1.sections.first()
        sec1.status = 1
        sec1.duration = 1
        sec1.save()
        sec1.meeting_times.clear()

        # class 2 is still unreviewed
        self.cls2 = self.program.classes()[2]
        self.cls2.teachers.set([self.teachers[1]])
        self.cls2.status = 0
        self.cls2.save()
        sec2 = self.cls2.sections.first()
        sec2.status = 0
        sec2.duration = 1
        sec2.save()

        # class 3 got rejected
        self.cls3 = self.program.classes()[3]
        self.cls3.teachers.set([self.teachers[1]])
        self.cls3.status = -10
        self.cls3.save()
        sec3 = self.cls3.sections.first()
        sec3.status = -10
        sec3.duration = 1
        sec3.save()

        self.teacher_checked_in_type, _ = RecordType.objects.get_or_create(
            name="teacher_checked_in",
            defaults={"description": "Teacher checked in for teaching"}
        )

    def test_get_filter(self):
        # make sure get_filter returns the right Q objects
        # unfiltered baseline
        filt = get_filter(self.program)
        self.assertEqual(ClassSubject.objects.filter(filt).distinct().count(), 4)

        # just the approved ones
        filt_approved = get_filter(self.program, approved=True)
        self.assertEqual(ClassSubject.objects.filter(filt_approved).distinct().count(), 2)

        # just the scheduled ones
        filt_scheduled = get_filter(self.program, scheduled=True)
        # class 0, 2, and 3 were scheduled by schedule_randomly
        self.assertEqual(ClassSubject.objects.filter(filt_scheduled).distinct().count(), 3)

        # filter by specific teachers
        filt_teachers = get_filter(self.program, teachers=[self.teachers[0]])
        self.assertEqual(ClassSubject.objects.filter(filt_teachers).distinct().count(), 2)

        # combine all filters
        filt_combined = get_filter(self.program, approved=True, scheduled=True, teachers=[self.teachers[0]])
        self.assertEqual(ClassSubject.objects.filter(filt_combined).distinct().count(), 1)

    def test_num_teachers_teaching(self):
        # count teachers with active classes (teacher 0 has approved, teacher 1 doesn't)
        self.assertEqual(TeacherBigBoardModule.num_teachers_teaching(self.program), 2)
        self.assertEqual(TeacherBigBoardModule.num_teachers_teaching(self.program, approved=True), 1)
        self.assertEqual(TeacherBigBoardModule.num_teachers_teaching(self.program, scheduled=True), 2)

    def test_num_class_reg(self):
        # test the registration count metrics
        # total classes should be 4
        self.assertEqual(TeacherBigBoardModule.num_class_reg(self.program), 4)
        # only 2 are approved
        self.assertEqual(TeacherBigBoardModule.num_class_reg(self.program, approved=True), 2)
        # 3 are scheduled
        self.assertEqual(TeacherBigBoardModule.num_class_reg(self.program, scheduled=True), 3)

    def test_reg_classes_and_teach_times(self):
        # test the graph timestamp arrays
        reg = self.module.reg_classes(self.program)
        self.assertEqual(len(reg), 4)
        reg_app = self.module.reg_classes(self.program, approved=True)
        self.assertEqual(len(reg_app), 2)

        teach = self.module.teach_times(self.program)
        self.assertEqual(len(teach), 2)
        teach_app = self.module.teach_times(self.program, approved=True)
        self.assertEqual(len(teach_app), 1)

    def test_get_hours_and_static_hours(self):
        # verify class hours math
        class_hours, student_hours = TeacherBigBoardModule.get_hours(self.program)
        self.assertEqual(len(class_hours), 4)
        self.assertEqual(len(student_hours), 4)

        # total hours is 4 since all 4 sections have duration 1
        sh = TeacherBigBoardModule.static_hours(self.program)
        self.assertEqual(sh[0], 4)

        # only 2 hours from the approved classes
        sh_app = TeacherBigBoardModule.static_hours(self.program, approved=True)
        self.assertEqual(sh_app[0], 2)

    def test_num_checked_in_teachers(self):
        # check teacher check-in metrics
        # starts at 0
        self.assertEqual(self.module.num_checked_in_teachers(self.program), 0)

        # log a check in
        Record.objects.create(
            program=self.program,
            user=self.teachers[0],
            event=self.teacher_checked_in_type,
            time=timezone.now()
        )
        # this yesterday checkin shouldn't count for today's metrics
        Record.objects.create(
            program=self.program,
            user=self.teachers[1],
            event=self.teacher_checked_in_type,
            time=timezone.now() - datetime.timedelta(days=1)
        )

        self.assertEqual(self.module.num_checked_in_teachers(self.program), 1)

    def test_caching_behavior(self):
        # make sure the caching decorator actually caches
        # baseline call
        self.assertEqual(TeacherBigBoardModule.num_class_reg(self.program), 4)

        # delete a class from the db directly
        self.cls3.delete()

        # count should still be 4 since it's pulling from cache
        self.assertEqual(TeacherBigBoardModule.num_class_reg(self.program), 4)

        # flush cache
        self._flush_cache()

        # now it hits the db and returns 3
        self.assertEqual(TeacherBigBoardModule.num_class_reg(self.program), 3)

    def test_teacherbigboard_view(self):
        # test the actual dashboard view rendering
        request = self.factory.get('/manage/teacherbigboard')
        request.user = self.admin
        request.program = self.program
        request.prog = self.program

        # pull the raw method out of the decorator to call it directly
        fn = getattr(TeacherBigBoardModule.teacherbigboard, 'method', TeacherBigBoardModule.teacherbigboard)

        response = fn(
            self.module, request, 'manage', None, None, None, None, self.program
        )

        response.context_data['prog'] = self.program
        response.context_data['popular_classes'] = None
        response.render()
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        self.assertIn("classes registered", content)
        self.assertIn("classes approved", content)
        self.assertIn("class-hours registered", content)
        self.assertTrue(len(content) > 0)

    def test_teacherbigboard_no_classes_edge_case(self):
        # verify the dashboard doesn't crash if there are zero classes
        ClassSubject.objects.filter(parent_program=self.program).delete()
        self._flush_cache()

        request = self.factory.get('/manage/teacherbigboard')
        request.user = self.admin
        request.program = self.program
        request.prog = self.program
        fn = getattr(TeacherBigBoardModule.teacherbigboard, 'method', TeacherBigBoardModule.teacherbigboard)
        response = fn(
            self.module, request, 'manage', None, None, None, None, self.program
        )

        response.context_data['prog'] = self.program
        response.context_data['popular_classes'] = None
        response.render()
        self.assertEqual(response.status_code, 200)
