"""
Tests for get_hours() N+1 fix and pass→continue bug fix (#3798).

Proves:
1. get_hours() uses bounded queries (prefetch_related) instead of N+1
2. Unapproved sections are excluded when approved=True (pass→continue fix)
3. Unscheduled sections are excluded when scheduled=True (pass→continue fix)
"""
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import Group

from esp.cal.models import Event, EventType
from esp.program.models import (
    ClassCategories, ClassSection, ClassSubject, Program,
)
from esp.program.modules.handlers.teacherbigboardmodule import (
    TeacherBigBoardModule,
)
from esp.tests.util import CacheFlushTestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian',
                  'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class GetHoursQueryCountTest(CacheFlushTestCase):
    """Proof: get_hours() should use O(1) queries via prefetch_related,
    not O(N) queries from per-class get_sections() + meeting_times.count()."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='gethours', name='GetHours Test', grade_min=7, grade_max=12)
        self.category = ClassCategories.objects.create(
            symbol='T', category='Test')
        self.program.class_categories.add(self.category)

        self.teacher = ESPUser.objects.create_user(
            username='gh_teacher', password='password', email='t@test.org')
        self.teacher.makeRole('Teacher')

        # Create 10 classes, each with 2 sections
        for i in range(10):
            cls = ClassSubject.objects.create(
                title='Class %d' % i, category=self.category,
                grade_min=7, grade_max=12, parent_program=self.program,
                class_size_max=30, class_info='Desc %d' % i,
                duration=Decimal('1.00'),
                timestamp=datetime(2025, 1, 1, 10, 0))
            cls.teachers.add(self.teacher)
            for j in range(2):
                ClassSection.objects.create(
                    parent_class=cls, status=10,
                    duration=Decimal('1.00'))

    def test_get_hours_bounded_queries(self):
        """get_hours() should execute a bounded number of queries
        regardless of number of classes/sections."""
        # Warm up any caches
        TeacherBigBoardModule.get_hours.delete_all()

        # With 10 classes x 2 sections:
        # BEFORE fix: 1 (classes) + 10 (get_sections) + 20 (meeting_times.count) = 31 queries
        # AFTER fix: 1 (classes) + 1 (prefetch sections) + 1 (prefetch meeting_times) = 3 queries
        with self.assertNumQueries(3):
            class_hours, student_hours = TeacherBigBoardModule.get_hours(self.program)

        self.assertEqual(len(class_hours), 10)
        self.assertEqual(len(student_hours), 10)
        # Each class has duration=1.0, class_size_max=30
        # section_sum = 2 sections x 1.0 = 2.0 per class
        for hours, ts in class_hours:
            self.assertEqual(hours, Decimal('2.00'))
        for hours, ts in student_hours:
            self.assertEqual(hours, Decimal('2.00') * 30)


class GetHoursApprovedFilterTest(CacheFlushTestCase):
    """Proof: get_hours(approved=True) should skip unapproved sections.

    BEFORE: `if approved and not sec.isAccepted(): pass` — no-op, duration
            of unapproved sections is still added.
    AFTER:  `if approved and sec.status <= 0: continue` — unapproved
            sections are correctly excluded.
    """

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='ghapproved', name='Approved Test', grade_min=7, grade_max=12)
        self.category = ClassCategories.objects.create(
            symbol='A', category='ApprTest')
        self.program.class_categories.add(self.category)

        self.teacher = ESPUser.objects.create_user(
            username='gh_teacher2', password='password', email='t2@test.org')
        self.teacher.makeRole('Teacher')

        # Create class with status>0 (approved)
        self.cls = ClassSubject.objects.create(
            title='Approved Class', category=self.category,
            grade_min=7, grade_max=12, parent_program=self.program,
            class_size_max=20, class_info='Desc',
            status=10, duration=Decimal('1.00'),
            timestamp=datetime(2025, 1, 1, 10, 0))
        self.cls.teachers.add(self.teacher)

        # Section 1: approved (status=10)
        self.sec_approved = ClassSection.objects.create(
            parent_class=self.cls, status=10,
            duration=Decimal('1.00'))

        # Section 2: NOT approved (status=0)
        self.sec_unapproved = ClassSection.objects.create(
            parent_class=self.cls, status=0,
            duration=Decimal('2.00'))

    def test_approved_excludes_unapproved_sections(self):
        """With approved=True, only approved sections should contribute hours."""
        TeacherBigBoardModule.get_hours.delete_all()

        class_hours, student_hours = TeacherBigBoardModule.get_hours(
            self.program, approved=True)

        # Only the approved section (1.0h) should count, not 1.0 + 2.0 = 3.0
        self.assertEqual(len(class_hours), 1)
        self.assertEqual(class_hours[0][0], Decimal('1.00'))

    def test_no_filter_includes_all_sections(self):
        """Without approved=True, all sections should contribute hours."""
        TeacherBigBoardModule.get_hours.delete_all()

        class_hours, student_hours = TeacherBigBoardModule.get_hours(
            self.program)

        # Both sections: 1.0 + 2.0 = 3.0
        self.assertEqual(len(class_hours), 1)
        self.assertEqual(class_hours[0][0], Decimal('3.00'))


class GetHoursScheduledFilterTest(CacheFlushTestCase):
    """Proof: get_hours(scheduled=True) should skip unscheduled sections.

    BEFORE: `if scheduled and sec.meeting_times.count() == 0: pass` — no-op,
            duration of unscheduled sections is still added.
    AFTER:  `if scheduled and len(sec.meeting_times.all()) == 0: continue` —
            unscheduled sections are correctly excluded.
    """

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='ghsched', name='Scheduled Test', grade_min=7, grade_max=12)
        self.category = ClassCategories.objects.create(
            symbol='S', category='SchedTest')
        self.program.class_categories.add(self.category)

        self.teacher = ESPUser.objects.create_user(
            username='gh_teacher3', password='password', email='t3@test.org')
        self.teacher.makeRole('Teacher')

        self.event_type, _ = EventType.objects.get_or_create(
            description='Class Time Slot')

        # Create an approved+scheduled class
        self.cls = ClassSubject.objects.create(
            title='Scheduled Class', category=self.category,
            grade_min=7, grade_max=12, parent_program=self.program,
            class_size_max=25, class_info='Desc',
            status=10, duration=Decimal('1.00'),
            timestamp=datetime(2025, 1, 1, 10, 0))
        self.cls.teachers.add(self.teacher)

        timeslot = Event.objects.create(
            start=datetime(2025, 6, 1, 10, 0),
            end=datetime(2025, 6, 1, 11, 0),
            short_description='Slot 1', description='Slot 1',
            name='Slot1', program=self.program, event_type=self.event_type)

        # Section 1: scheduled (has meeting time), approved
        self.sec_scheduled = ClassSection.objects.create(
            parent_class=self.cls, status=10,
            duration=Decimal('1.00'))
        self.sec_scheduled.meeting_times.add(timeslot)

        # Section 2: NOT scheduled (no meeting times), approved
        self.sec_unscheduled = ClassSection.objects.create(
            parent_class=self.cls, status=10,
            duration=Decimal('2.00'))

    def test_scheduled_excludes_unscheduled_sections(self):
        """With scheduled=True, only scheduled sections should contribute hours."""
        TeacherBigBoardModule.get_hours.delete_all()

        class_hours, student_hours = TeacherBigBoardModule.get_hours(
            self.program, approved=True, scheduled=True)

        # Only the scheduled section (1.0h) should count
        self.assertEqual(len(class_hours), 1)
        self.assertEqual(class_hours[0][0], Decimal('1.00'))

    def test_no_scheduled_filter_includes_all(self):
        """Without scheduled=True, all sections contribute hours."""
        TeacherBigBoardModule.get_hours.delete_all()

        class_hours, student_hours = TeacherBigBoardModule.get_hours(
            self.program)

        # Both sections: 1.0 + 2.0 = 3.0
        self.assertEqual(len(class_hours), 1)
        self.assertEqual(class_hours[0][0], Decimal('3.00'))


class StaticHoursTest(CacheFlushTestCase):
    """Verify static_hours() correctly sums get_hours() output."""

    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(
            url='statichrs', name='Static Hours Test', grade_min=7, grade_max=12)
        self.category = ClassCategories.objects.create(
            symbol='H', category='HoursTest')
        self.program.class_categories.add(self.category)

        self.teacher = ESPUser.objects.create_user(
            username='gh_teacher4', password='password', email='t4@test.org')
        self.teacher.makeRole('Teacher')

        # 3 classes: durations 1.0, 2.0, 1.5; capacities 20, 30, 10
        for i, (dur, cap) in enumerate([(1, 20), (2, 30), (1.5, 10)]):
            cls = ClassSubject.objects.create(
                title='SH Class %d' % i, category=self.category,
                grade_min=7, grade_max=12, parent_program=self.program,
                class_size_max=cap, class_info='Desc',
                duration=Decimal(str(dur)),
                timestamp=datetime(2025, 1, 1, 10 + i, 0))
            cls.teachers.add(self.teacher)
            ClassSection.objects.create(
                parent_class=cls, status=10,
                duration=Decimal(str(dur)))

    def test_static_hours_sums(self):
        """static_hours() should return [total_class_hours, total_student_hours]."""
        TeacherBigBoardModule.get_hours.delete_all()
        TeacherBigBoardModule.static_hours.delete_all()

        result = TeacherBigBoardModule.static_hours(self.program)

        # class hours: 1.0 + 2.0 + 1.5 = 4.5
        self.assertEqual(result[0], Decimal('4.50'))
        # student hours: 1.0*20 + 2.0*30 + 1.5*10 = 20 + 60 + 15 = 95
        self.assertEqual(result[1], Decimal('95.00'))
