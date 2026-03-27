import datetime
from collections import Counter

from esp.program.models import ClassSection, RegistrationType, StudentRegistration
from esp.program.modules.handlers.onsiteattendance import OnSiteAttendance
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class OnSiteAttendanceTest(ProgramFrameworkTest):
    """
    Regression tests for `OnSiteAttendance.times_attending_class()` and
    `OnSiteAttendance.times_checked_in()`.

    These tests validate real data aggregation by hour buckets, ordering, and
    duplicate prevention.
    """

    def setUp(self):
        # Use hour-aligned timeslots so the handler's `replace(minute=0, ...)`
        # truncation produces deterministic buckets.
        super().setUp(
            num_timeslots=4,
            timeslot_length=60,
            timeslot_gap=0,
            num_rooms=1,
            room_capacity=30,
            num_categories=1,
            num_teachers=1,
            classes_per_teacher=1,
            sections_per_class=1,
            num_students=3,
            num_admins=1,
            program_type="TestProgram",
            program_instance_name="2222_Summer",
            program_instance_label="Summer 2222",
            start_time=datetime.datetime(2026, 3, 20, 9, 0, 0),
        )

        self.module = OnSiteAttendance()

        self.attended_sr_type = RegistrationType.get_cached(
            name="Attended", category="student"
        )
        self.attended_record_type = RecordType.objects.get(name="attended")

        self.section = (
            ClassSection.objects.filter(parent_class__parent_program=self.program)
            .order_by("id")
            .first()
        )
        self.assertIsNotNone(self.section, "ProgramFrameworkTest must create at least one section")

        # Assign two consecutive hour-aligned Events to the section so
        # `section.end_time().end` lands on an hour boundary.
        time_slots = list(self.program.getTimeSlots().order_by("start"))
        self.section.assign_meeting_times(time_slots[:2])

    def _make_attended_registration(self, student, when):
        """
        Create a real attendance SR row so `times_attending_class()` uses
        the same queries as production.
        """
        return StudentRegistration.objects.create(
            user=student,
            section=self.section,
            relationship=self.attended_sr_type,
            start_date=when,
        )

    def _make_checked_in_record(self, student, when):
        """Create a real program 'attended' Record row."""
        return Record.objects.create(
            event=self.attended_record_type,
            program=self.program,
            user=student,
            time=when,
        )

    def _bucket_hour(self, dt):
        """Truncate minutes/seconds to the handler's hour-bucket granularity."""
        return dt.replace(minute=0, second=0, microsecond=0)

    def _section_end_bucket_for_date(self, reference_dt):
        """
        Compute the end hour bucket for this section.

        The handler uses the section's end time and counts the final hour
        bucket as well; for these tests we assume the program date matches
        `reference_dt` (set by ProgramFrameworkTest).
        """
        end_dt = self.section.end_time().end
        _ = reference_dt  # Keep signature stable for callers; end date is already determined by the section.
        return self._bucket_hour(end_dt)

    def _expected_attending_buckets(self, attendance_when_by_user):
        """
        Given real attendance start datetimes per user, compute:
          - the expected hour buckets (chronological)
          - each user's earliest bucket start

        Handler behavior:
        - for each attendance SR, it starts counting at sr.start_date hour-truncation
        - counts the student each hour until the end bucket
        - prevents duplicate counting per student per bucket
        """
        user_start_buckets = {
            user: min(self._bucket_hour(dt) for dt in when_list)
            for user, when_list in attendance_when_by_user.items()
        }
        min_bucket = min(user_start_buckets.values())
        reference_dt = next(iter(attendance_when_by_user.values()))[0]
        end_bucket = self._section_end_bucket_for_date(reference_dt)

        buckets = []
        t = min_bucket
        while t <= end_bucket:
            buckets.append(t)
            t += datetime.timedelta(hours=1)
        return buckets, user_start_buckets

    def test_times_attending_class_groups_orders_hour_buckets(self):
        # Student 0 & 1 are marked within the 09:xx hour; student 2 within 10:xx.
        s0, s1, s2 = self.students

        attendance_when_by_user = {
            s0: [datetime.datetime(2026, 3, 20, 9, 15, 30)],
            s1: [datetime.datetime(2026, 3, 20, 9, 45, 0)],
            s2: [datetime.datetime(2026, 3, 20, 10, 5, 10)],
        }
        for user, when_list in attendance_when_by_user.items():
            for when in when_list:
                self._make_attended_registration(user, when)

        result = self.module.times_attending_class(self.program)

        expected_buckets, user_start_buckets = self._expected_attending_buckets(
            attendance_when_by_user
        )

        self.assertEqual(set(result.keys()), set(expected_buckets))
        self.assertEqual(list(result.keys()), sorted(result.keys()))

        for bucket in expected_buckets:
            expected_user_ids = {
                user.id
                for user, start_bucket in user_start_buckets.items()
                if bucket >= start_bucket
            }
            actual_user_ids = {u.id for u in result[bucket]}

            self.assertEqual(
                len(actual_user_ids),
                len(result[bucket]),
                f"Duplicate counting detected in bucket {bucket!r}",
            )
            self.assertEqual(
                actual_user_ids,
                expected_user_ids,
                f"Wrong attendees counted for bucket {bucket!r}",
            )

    def test_times_attending_class_does_not_duplicate_user_per_hour_bucket(self):
        # Mark the same student twice within the same hour bucket.
        student = self.students[0]
        when_list = [
            datetime.datetime(2026, 3, 20, 9, 10, 0),
            datetime.datetime(2026, 3, 20, 9, 55, 0),
        ]
        attendance_when_by_user = {student: when_list}
        for when in when_list:
            self._make_attended_registration(student, when)

        result = self.module.times_attending_class(self.program)
        expected_buckets, _ = self._expected_attending_buckets(
            attendance_when_by_user
        )
        self.assertEqual(set(result.keys()), set(expected_buckets))
        self.assertEqual(list(result.keys()), sorted(result.keys()))

        for bucket in expected_buckets:
            self.assertEqual(
                len(result[bucket]),
                1,
                f"Duplicate counting detected for bucket {bucket!r}",
            )
            self.assertEqual(
                result[bucket].count(student),
                1,
                f"Student appears more than once in bucket {bucket!r}",
            )

    def test_times_checked_in_min_time_per_user_ordered_and_bucketed_by_hour(self):
        s0, s1, s2 = self.students

        records_when_by_user = {
            s0: [
                datetime.datetime(2026, 3, 20, 9, 12, 30),
                datetime.datetime(2026, 3, 20, 9, 5, 10),
            ],
            s1: [datetime.datetime(2026, 3, 20, 10, 0, 5)],
            s2: [
                datetime.datetime(2026, 3, 20, 10, 59, 59),
                datetime.datetime(2026, 3, 20, 11, 0, 0),
            ],
        }
        for user, when_list in records_when_by_user.items():
            for when in when_list:
                self._make_checked_in_record(user, when)

        result = self.module.times_checked_in(self.program)

        expected_min_times = sorted(
            min(when_list) for when_list in records_when_by_user.values()
        )
        self.assertEqual(result, expected_min_times)

        self.assertEqual(len(result), len(records_when_by_user))
        self.assertEqual(result, sorted(result), "Result times must be chronological.")

        # Bucket by hour (truncate minutes/seconds) to validate grouping.
        bucket_counts = Counter(self._bucket_hour(t) for t in result)
        expected_bucket_counts = Counter(self._bucket_hour(t) for t in expected_min_times)

        self.assertEqual(bucket_counts, expected_bucket_counts)
        self.assertEqual(list(bucket_counts.keys()), sorted(bucket_counts.keys()))

    def test_times_empty_data(self):
        # No attendance SRs and no check-in Records created in setUp().
        attending = self.module.times_attending_class(self.program)
        total_attendees = sum(len(users) for users in attending.values())
        self.assertEqual(total_attendees, 0)

        checked_in = self.module.times_checked_in(self.program)
        self.assertEqual(len(checked_in), 0)

