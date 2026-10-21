import datetime
from unittest.mock import patch

from django.test import RequestFactory
from django.utils import timezone

from esp.program.models import (
    RegistrationType,
    StudentRegistration,
    StudentSubjectInterest,
)
from esp.program.modules.admin_search import (
    AdminSearchEntry,
    SEARCH_CATEGORY_REGISTRATION,
)
from esp.program.modules.handlers.bigboardmodule import BigBoardModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class BigBoardModuleTests(ProgramFrameworkTest):
    """Unit tests for BigBoardModule metrics, caching, and dashboard view."""

    def setUp(self):
        super().setUp(
            num_timeslots=2,
            num_teachers=2,
            classes_per_teacher=1,
            sections_per_class=1,
            num_rooms=2,
            num_students=3,
        )
        self.factory = RequestFactory()
        self.admin = self.admins[0]
        self.module = BigBoardModule()

        self._flush_cache()

        self.schedule_randomly()

        self.cls0 = self.program.classes()[0]
        self.sec0 = self.cls0.sections.first()

        self.enrolled_rt, _ = RegistrationType.objects.get_or_create(
            name='Enrolled', defaults={'category': 'student'}
        )
        self.interested_rt, _ = RegistrationType.objects.get_or_create(
            name='Interested', defaults={'category': 'student'}
        )
        self.priority_rt, _ = RegistrationType.objects.get_or_create(
            name='Priority/1', defaults={'category': 'student'}
        )

        self.med_type, _ = RecordType.objects.get_or_create(
            name='med', defaults={'description': 'Medical form submitted'}
        )
        self.med_bypass_type, _ = RecordType.objects.get_or_create(
            name='med_bypass', defaults={'description': 'Medical form bypassed'}
        )
        self.attended_type, _ = RecordType.objects.get_or_create(
            name='attended', defaults={'description': 'Student attended'}
        )

    def test_module_properties(self):
        props = BigBoardModule.module_properties()
        self.assertEqual(props["admin_title"], "Student Registration Big Board")
        self.assertEqual(props["link_title"], "Watch incoming student registrations")
        self.assertEqual(props["module_type"], "manage")
        self.assertEqual(props["seq"], 10)
        self.assertEqual(props["choosable"], 1)

    def test_get_admin_search_entry(self):
        entry = BigBoardModule.get_admin_search_entry(
            self.program, 'manage', 'bigboard', None
        )
        self.assertIsInstance(entry, AdminSearchEntry)
        self.assertEqual(entry.id, "manage_bigboard")
        self.assertEqual(entry.title, "Student Registration Big Board")
        self.assertEqual(entry.category, SEARCH_CATEGORY_REGISTRATION)
        self.assertIn("big board", entry.keywords)
        self.assertIn("/manage/", entry.url)

        other_entry = BigBoardModule.get_admin_search_entry(
            self.program, 'manage', 'other_view', None
        )
        self.assertIsNone(other_entry)

    def test_is_step(self):
        self.assertFalse(self.module.isStep())

    def test_users_enrolled_and_num_users_enrolled(self):
        self.assertEqual(BigBoardModule.num_users_enrolled(self.module, self.program), 0)
        self.assertEqual(list(BigBoardModule.users_enrolled(self.program)), [])

        StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )
        StudentRegistration.objects.create(
            user=self.students[1],
            section=self.sec0,
            relationship=self.interested_rt,
        )

        self._flush_cache()
        enrolled_users = list(BigBoardModule.users_enrolled(self.program))
        self.assertEqual(enrolled_users, [self.students[0].id])
        self.assertEqual(BigBoardModule.num_users_enrolled(self.module, self.program), 1)

    def test_users_with_lottery_and_num_users_with_lottery(self):
        StudentSubjectInterest.objects.create(
            user=self.students[0],
            subject=self.cls0,
        )
        StudentRegistration.objects.create(
            user=self.students[1],
            section=self.sec0,
            relationship=self.priority_rt,
        )
        StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.interested_rt,
        )
        # Enrolled-only negative control: student 2 should not be counted
        StudentRegistration.objects.create(
            user=self.students[2],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )

        self._flush_cache()
        users = BigBoardModule.users_with_lottery(self.program)
        self.assertEqual(users, {self.students[0].id, self.students[1].id})
        self.assertEqual(self.module.num_users_with_lottery(self.program), 2)

    def test_num_active_users(self):
        now = timezone.now()
        self.assertEqual(self.module.num_active_users(self.program, minutes=10), 0)

        ssi = StudentSubjectInterest.objects.create(
            user=self.students[0],
            subject=self.cls0,
        )
        ssi.start_date = now
        ssi.save()

        sr = StudentRegistration.objects.create(
            user=self.students[1],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )
        sr.start_date = now
        sr.save()

        Record.objects.create(
            program=self.program,
            user=self.students[2],
            event=self.med_type,
            time=now,
        )

        self._flush_cache()
        self.assertEqual(self.module.num_active_users(self.program, minutes=10), 3)

        old_time = now - datetime.timedelta(minutes=30)
        ssi.start_date = old_time
        ssi.save()
        sr.start_date = old_time
        sr.save()
        Record.objects.filter(program=self.program).update(time=old_time)

        self._flush_cache()
        self.assertEqual(self.module.num_active_users(self.program, minutes=10), 0)

    def test_num_ssis(self):
        self.assertEqual(self.module.num_ssis(self.program), 0)

        StudentSubjectInterest.objects.create(
            user=self.students[0],
            subject=self.cls0,
        )
        StudentSubjectInterest.objects.create(
            user=self.students[1],
            subject=self.cls0,
        )

        self._flush_cache()
        self.assertEqual(self.module.num_ssis(self.program), 2)

    def test_num_priority_selections(self):
        self.assertEqual(self.module.num_priority_selections(self.program), 0)

        StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.priority_rt,
        )
        priority_2, _ = RegistrationType.objects.get_or_create(
            name='Priority/2', defaults={'category': 'student'}
        )
        StudentRegistration.objects.create(
            user=self.students[1],
            section=self.sec0,
            relationship=priority_2,
        )
        StudentRegistration.objects.create(
            user=self.students[2],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )

        self._flush_cache()
        self.assertEqual(self.module.num_priority_selections(self.program), 2)

    def test_num_prefs(self):
        self.assertEqual(self.module.num_prefs(self.program), 0)

        StudentSubjectInterest.objects.create(
            user=self.students[0],
            subject=self.cls0,
        )
        StudentRegistration.objects.create(
            user=self.students[1],
            section=self.sec0,
            relationship=self.priority_rt,
        )
        StudentRegistration.objects.create(
            user=self.students[2],
            section=self.sec0,
            relationship=self.interested_rt,
        )
        StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )

        self._flush_cache()
        # num_prefs = num_srs (Interested + Priority) + num_ssis = 2 + 1 = 3
        self.assertEqual(self.module.num_prefs(self.program), 3)

    def test_num_medical_and_times_medical(self):
        self.assertEqual(self.module.num_medical(self.program), 0)
        self.assertEqual(self.module.times_medical(self.program), [])

        t1 = timezone.now() - datetime.timedelta(hours=2)
        t2 = timezone.now() - datetime.timedelta(hours=1)

        Record.objects.create(
            program=self.program,
            user=self.students[0],
            event=self.med_type,
            time=t1,
        )
        Record.objects.create(
            program=self.program,
            user=self.students[1],
            event=self.med_bypass_type,
            time=t2,
        )
        Record.objects.create(
            program=self.program,
            user=self.students[2],
            event=self.attended_type,
            time=t1,
        )

        self._flush_cache()
        self.assertEqual(self.module.num_medical(self.program), 2)
        times = self.module.times_medical(self.program)
        self.assertEqual(len(times), 2)
        self.assertEqual(times[0], t1)
        self.assertEqual(times[1], t2)

    def test_checked_in_users_and_num_checked_in_users(self):
        self.assertEqual(self.module.num_checked_in_users(self.program), 0)
        self.assertEqual(list(BigBoardModule.checked_in_users(self.program)), [])

        Record.objects.create(
            program=self.program,
            user=self.students[0],
            event=self.attended_type,
            time=timezone.now(),
        )
        Record.objects.create(
            program=self.program,
            user=self.students[0],
            event=self.attended_type,
            time=timezone.now(),
        )
        Record.objects.create(
            program=self.program,
            user=self.students[1],
            event=self.attended_type,
            time=timezone.now(),
        )

        self._flush_cache()
        self.assertEqual(self.module.num_checked_in_users(self.program), 2)
        checked_in = set(BigBoardModule.checked_in_users(self.program))
        self.assertEqual(checked_in, {self.students[0].id, self.students[1].id})

    def test_times_lottery(self):
        t1 = timezone.now() - datetime.timedelta(hours=3)
        t2 = timezone.now() - datetime.timedelta(hours=2)
        t3 = timezone.now() - datetime.timedelta(hours=1)

        ssi = StudentSubjectInterest.objects.create(
            user=self.students[0],
            subject=self.cls0,
        )
        ssi.start_date = t1
        ssi.save()

        sr = StudentRegistration.objects.create(
            user=self.students[1],
            section=self.sec0,
            relationship=self.priority_rt,
        )
        sr.start_date = t2
        sr.save()

        sr0 = StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.priority_rt,
        )
        sr0.start_date = t3
        sr0.save()

        self._flush_cache()
        lottery_times = self.module.times_lottery(self.program)
        self.assertEqual(len(lottery_times), 2)
        self.assertEqual(lottery_times[0], t1)
        self.assertEqual(lottery_times[1], t2)

    def test_times_enrolled(self):
        t1 = timezone.now() - datetime.timedelta(hours=4)
        t2 = timezone.now() - datetime.timedelta(hours=2)

        sr1 = StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )
        sr1.start_date = t1
        sr1.save()

        sr2 = StudentRegistration.objects.create(
            user=self.students[1],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )
        sr2.start_date = t2
        sr2.save()

        self._flush_cache()
        enrolled_times = self.module.times_enrolled(self.program)
        self.assertEqual(len(enrolled_times), 2)
        self.assertEqual(enrolled_times[0], t1)
        self.assertEqual(enrolled_times[1], t2)

    def test_chunk_times_cumulative_and_non_cumulative(self):
        base = datetime.datetime(2026, 1, 1, 10, 0, 0)
        times = [
            (1, base + datetime.timedelta(minutes=15)),
            (2, base + datetime.timedelta(minutes=45)),
            (1, base + datetime.timedelta(hours=1, minutes=20)),
        ]
        start = base
        end = base + datetime.timedelta(hours=2)

        chunks_cum = BigBoardModule.chunk_times(
            times, start, end, delta=datetime.timedelta(hours=1), cumulative=True
        )
        self.assertEqual(chunks_cum, [0.0, 3.0, 4.0])

        chunks_non_cum = BigBoardModule.chunk_times(
            times, start, end, delta=datetime.timedelta(hours=1), cumulative=False
        )
        self.assertEqual(chunks_non_cum, [0.0, 3.0, 1.0])

    def test_make_graph_data(self):
        graph_data, start = BigBoardModule.make_graph_data([], cutoff=1)
        self.assertEqual(graph_data, [])
        self.assertIsNone(start)

        t1 = datetime.datetime(2026, 1, 1, 10, 30, 0)
        t2 = datetime.datetime(2026, 1, 1, 14, 0, 0)
        series = [
            ("Enrolled", [(1, t1), (1, t2)], True),
        ]
        graph_data, start = BigBoardModule.make_graph_data(
            series, drop_beg=0, drop_end=0, cutoff=1
        )
        self.assertEqual(len(graph_data), 1)
        self.assertEqual(graph_data[0]["description"], "Enrolled")
        self.assertIsInstance(graph_data[0]["data"], list)
        self.assertEqual(start, datetime.datetime(2026, 1, 1, 0, 0, 0))

    def test_load_averages_success(self):
        with patch('subprocess.check_output',
                   return_value=b' 12:00:00 up 10 days, 2 users,  load average: 0.15, 0.45, 1.20\n'):
            loads = self.module.load_averages()
            self.assertEqual(loads, [0.15, 0.45, 1.20])

    def test_load_averages_exception_fallback(self):
        with patch('subprocess.check_output', side_effect=OSError('uptime failed')):
            loads = self.module.load_averages()
            self.assertEqual(loads, [])

    def test_popular_classes_and_wrapper(self):
        self.sec0.meeting_times.set(self.timeslots)

        StudentSubjectInterest.objects.create(
            user=self.students[0],
            subject=self.cls0,
        )
        StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.priority_rt,
        )
        StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )

        self._flush_cache()
        popular = self.module.popular_classes(self.program)
        self.assertIsInstance(popular, list)
        descs = [item[0] for item in popular]
        self.assertIn("number of stars", descs)
        self.assertIn("number of priority selections", descs)
        self.assertIn("number of enrollments", descs)

        wrapped = self.module.popular_classes_wrapper(self.program)
        self.assertEqual(wrapped, popular)

    def test_caching_behavior(self):
        self.assertEqual(BigBoardModule.num_users_enrolled(self.module, self.program), 0)

        sr = StudentRegistration.objects.create(
            user=self.students[0],
            section=self.sec0,
            relationship=self.enrolled_rt,
        )

        self._flush_cache()
        self.assertEqual(BigBoardModule.num_users_enrolled(self.module, self.program), 1)

        sr.delete()

        self.assertEqual(BigBoardModule.num_users_enrolled(self.module, self.program), 1)

        self._flush_cache()
        self.assertEqual(BigBoardModule.num_users_enrolled(self.module, self.program), 0)

    def test_bigboard_view_rendering(self):
        request = self.factory.get('/manage/bigboard')
        request.user = self.admin
        request.program = self.program
        request.prog = self.program
        request.session = {}

        response = self.module.bigboard(
            request, 'manage', None, None, None, None, self.program
        )

        expected_keys = [
            'type',
            'numbers',
            'popular_classes',
            'first_hour',
            'left_axis_data',
            'loads',
            'timeslots',
            'categories',
        ]
        for key in expected_keys:
            self.assertIn(key, response.context_data)

        response.context_data['prog'] = self.program
        response.render()
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        self.assertIn("Registration Summary", content)
        self.assertIn("Student", content)

    def test_bigboard_view_non_admin_denied(self):
        request = self.factory.get('/manage/bigboard')
        request.user = self.students[0]
        request.program = self.program
        request.prog = self.program
        request.session = {}

        response = self.module.bigboard(
            request, 'manage', None, None, None, None, self.program
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn("not an administrator", content.lower())

    def test_bigboard_no_registrations_edge_case(self):
        StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program
        ).delete()
        StudentSubjectInterest.objects.filter(
            subject__parent_program=self.program
        ).delete()
        Record.objects.filter(program=self.program).delete()
        self._flush_cache()

        request = self.factory.get('/manage/bigboard')
        request.user = self.admin
        request.program = self.program
        request.prog = self.program
        request.session = {}

        response = self.module.bigboard(
            request, 'manage', None, None, None, None, self.program
        )

        expected_keys = [
            'type',
            'numbers',
            'popular_classes',
            'first_hour',
            'left_axis_data',
            'loads',
            'timeslots',
            'categories',
        ]
        for key in expected_keys:
            self.assertIn(key, response.context_data)

        response.context_data['prog'] = self.program
        response.render()
        self.assertEqual(response.status_code, 200)
