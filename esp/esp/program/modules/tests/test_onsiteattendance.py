__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2014 by the individual contributors
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
from esp.program.models import ClassSection, RegistrationType, StudentRegistration
from esp.program.modules.handlers.onsiteattendance import OnSiteAttendance
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class _OnSiteAttendanceBase(ProgramFrameworkTest):
    """
    Shared fixtures for OnSiteAttendance regression tests.

    Timeslot layout (hour-aligned, zero-gap, starting 09:00):
        slot 0: 09:00 – 10:00
        slot 1: 10:00 – 11:00  ← self.section end_time().end
        slot 2: 11:00 – 12:00
        slot 3: 12:00 – 13:00

    self.section spans slots 0–1, so times_attending_class() counts a student
    in every bucket from their sr.start_date hour up to and including 11:00.
    """

    def setUp(self):
        super().setUp(
            num_timeslots=4,       # 09:00, 10:00, 11:00, 12:00
            timeslot_length=60,    # 60-minute slots → hour-aligned boundaries
            timeslot_gap=0,        # no gap → consecutive hours
            num_rooms=1,
            room_capacity=30,
            num_categories=1,
            num_teachers=1,
            classes_per_teacher=2,  # 2 sections so unscheduled-section test has a spare
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
        self.assertIsNotNone(
            self.section,
            "ProgramFrameworkTest must create at least one section.",
        )
        time_slots = list(self.program.getTimeSlots().order_by("start"))
        self.section.assign_meeting_times(time_slots[:2])  # 09:00–11:00

    def tearDown(self):
        StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program,
            relationship=self.attended_sr_type,
        ).delete()
        Record.objects.filter(
            program=self.program, event=self.attended_record_type
        ).delete()
        super().tearDown()

    # ------------------------------------------------------------------ #
    # Fixture helpers                                                      #
    # ------------------------------------------------------------------ #

    def _make_sr(self, student, when, section=None):
        """Create an 'Attended' StudentRegistration at the given datetime."""
        return StudentRegistration.objects.create(
            user=student,
            section=section or self.section,
            relationship=self.attended_sr_type,
            start_date=when,
        )

    def _make_record(self, student, when):
        """Create a program 'attended' Record at the given datetime."""
        return Record.objects.create(
            event=self.attended_record_type,
            program=self.program,
            user=student,
            time=when,
        )

    def _make_other_program(self, program_type="OtherProgram",
                            instance_name="2222_Fall",
                            instance_label="Fall 2222",
                            num_timeslots=2):
        """Spin up a minimal second program and return it."""
        other = ProgramFrameworkTest()
        other.setUp(
            num_timeslots=num_timeslots,
            timeslot_length=60,
            timeslot_gap=0,
            num_rooms=1,
            room_capacity=10,
            num_categories=1,
            num_teachers=1,
            classes_per_teacher=1,
            sections_per_class=1,
            num_students=1,
            num_admins=1,
            program_type=program_type,
            program_instance_name=instance_name,
            program_instance_label=instance_label,
            start_time=datetime.datetime(2026, 3, 20, 9, 0, 0),
        )
        return other

    # ------------------------------------------------------------------ #
    # Assertion helpers                                                    #
    # ------------------------------------------------------------------ #

    def _bucket(self, dt):
        """Mirror the handler's hour-truncation: replace(minute=0, second=0, microsecond=0)."""
        return dt.replace(minute=0, second=0, microsecond=0)

    def _expected_buckets(self, start_dt, section=None):
        """
        Return the ordered list of hour buckets the handler emits for one SR
        with start_date=start_dt attending `section` (defaults to self.section).
        """
        s = section or self.section
        start_bucket = self._bucket(start_dt)
        end_bucket = self._bucket(s.end_time().end)
        buckets, t = [], start_bucket
        while t <= end_bucket:
            buckets.append(t)
            t += datetime.timedelta(hours=1)
        return buckets

    def assertBucketsOrdered(self, result):
        """Assert that result dict keys are in ascending chronological order."""
        keys = list(result.keys())
        self.assertEqual(keys, sorted(keys), "Bucket keys must be chronologically ordered.")

    def assertNoDuplicatesInBuckets(self, result):
        """Assert that no user appears more than once in any single bucket."""
        for bucket, users in result.items():
            user_ids = [u.id for u in users]
            self.assertEqual(
                len(user_ids), len(set(user_ids)),
                f"Duplicate user in bucket {bucket!r}: {user_ids}",
            )

    def assertUserInBuckets(self, user, buckets, result):
        """Assert that `user` appears in every listed bucket of `result`."""
        for b in buckets:
            self.assertIn(b, result, f"Expected bucket {b!r} missing from result.")
            self.assertIn(user, result[b], f"User missing from bucket {b!r}.")

    def assertUserNotInResult(self, user, result):
        """Assert that `user` does not appear in any bucket of `result`."""
        for bucket, users in result.items():
            self.assertNotIn(
                user, users,
                f"User unexpectedly present in bucket {bucket!r}.",
            )


class TestTimesAttendingClass(_OnSiteAttendanceBase):
    """
    Regression tests for OnSiteAttendance.times_attending_class().

    Invariants under test:
      - Returns dict; empty when no SRs exist.
      - Keys are chronologically ordered (graph rendering depends on this).
      - Each student is counted in every bucket from their attendance hour
        through the section's end-time bucket (carry-forward logic).
      - A student is counted at most once per bucket (deduplication).
      - SRs for unscheduled sections (no meeting_times) are excluded.
      - SRs from a different program are excluded.
      - Cross-midnight sections: end_time is shifted +1 day when
        section_end_dt.time() < sr.start_date.time().
      - Records with end_time < start_time after adjustment are skipped.
    """

    def test_no_registrations_returns_empty_dict(self):
        """Empty program → empty dict (not None, not [])."""
        result = self.module.times_attending_class(self.program)
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})

    def test_single_student_appears_in_all_buckets_until_section_end(self):
        """Student marked at 09:15 appears in 09:00, 10:00, 11:00 (section ends 11:00)."""
        student = self.students[0]
        when = datetime.datetime(2026, 3, 20, 9, 15, 0)
        self._make_sr(student, when)

        result = self.module.times_attending_class(self.program)

        expected = self._expected_buckets(when)
        self.assertEqual(sorted(result.keys()), expected)
        for b in expected:
            self.assertEqual(result[b], [student])

    def test_result_keys_are_chronologically_ordered(self):
        """Dict keys must be ascending — the BigBoard graph depends on this."""
        s0, s1, s2 = self.students
        self._make_sr(s0, datetime.datetime(2026, 3, 20, 9, 5, 0))
        self._make_sr(s1, datetime.datetime(2026, 3, 20, 10, 5, 0))
        self._make_sr(s2, datetime.datetime(2026, 3, 20, 11, 5, 0))

        self.assertBucketsOrdered(self.module.times_attending_class(self.program))

    def test_students_grouped_into_correct_buckets(self):
        """
        s0 @ 09:15, s1 @ 09:45, s2 @ 10:05; section ends 11:00.

        09:00 → {s0, s1}
        10:00 → {s0, s1, s2}   (carry-forward)
        11:00 → {s0, s1, s2}
        """
        s0, s1, s2 = self.students
        self._make_sr(s0, datetime.datetime(2026, 3, 20, 9, 15, 0))
        self._make_sr(s1, datetime.datetime(2026, 3, 20, 9, 45, 0))
        self._make_sr(s2, datetime.datetime(2026, 3, 20, 10, 5, 0))

        result = self.module.times_attending_class(self.program)
        self.assertBucketsOrdered(result)

        b9  = datetime.datetime(2026, 3, 20, 9, 0, 0)
        b10 = datetime.datetime(2026, 3, 20, 10, 0, 0)
        b11 = datetime.datetime(2026, 3, 20, 11, 0, 0)

        self.assertEqual({u.id for u in result[b9]},  {s0.id, s1.id})
        self.assertEqual({u.id for u in result[b10]}, {s0.id, s1.id, s2.id})
        self.assertEqual({u.id for u in result[b11]}, {s0.id, s1.id, s2.id})

    def test_deduplicates_same_student_same_hour(self):
        """Two SRs for the same student within one hour → counted once per bucket."""
        student = self.students[0]
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 10, 0))
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 55, 0))

        result = self.module.times_attending_class(self.program)
        self.assertNoDuplicatesInBuckets(result)
        # Student must still appear — dedup must not silently drop them.
        self.assertUserInBuckets(student, self._expected_buckets(
            datetime.datetime(2026, 3, 20, 9, 10, 0)
        ), result)

    def test_deduplicates_same_student_across_different_hours(self):
        """Two SRs in different hours → carry-forward, but still once per bucket."""
        student = self.students[0]
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 5, 0))
        self._make_sr(student, datetime.datetime(2026, 3, 20, 10, 5, 0))

        result = self.module.times_attending_class(self.program)
        self.assertNoDuplicatesInBuckets(result)
        # Student must appear from their earliest SR onward.
        self.assertUserInBuckets(student, self._expected_buckets(
            datetime.datetime(2026, 3, 20, 9, 5, 0)
        ), result)

    def test_excludes_sr_for_unscheduled_section(self):
        """SR whose section has no meeting_times must not appear (meeting_times__isnull=False filter)."""
        # Use a section that is explicitly different from self.section.
        unscheduled = (
            ClassSection.objects.filter(parent_class__parent_program=self.program)
            .order_by("id")
            .exclude(pk=self.section.pk)
            .first()
        )
        self.assertIsNotNone(
            unscheduled,
            "Need at least 2 sections; check classes_per_teacher in setUp.",
        )
        unscheduled.clear_meeting_times()

        student = self.students[0]
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 0, 0),
                      section=unscheduled)

        self.assertUserNotInResult(
            student, self.module.times_attending_class(self.program)
        )

    def test_excludes_sr_from_different_program(self):
        """SR belonging to another program must not bleed into self.program's result."""
        other = self._make_other_program()
        other_section = (
            ClassSection.objects.filter(parent_class__parent_program=other.program)
            .order_by("id").first()
        )
        other_section.assign_meeting_times(
            list(other.program.getTimeSlots().order_by("start"))[:2]
        )

        StudentRegistration.objects.create(
            user=self.students[0],
            section=other_section,
            relationship=self.attended_sr_type,
            start_date=datetime.datetime(2026, 3, 20, 9, 0, 0),
        )

        # self.program has no SRs of its own → must be empty.
        self.assertEqual(
            self.module.times_attending_class(self.program), {},
            "SR from a different program leaked into times_attending_class().",
        )

    def test_cross_midnight_section_shifts_end_time_forward_one_day(self):
        """
        Regression for the cross-midnight branch:
            if section_end_dt.time() < start_time.time():
                end_time += timedelta(days=1)

        Section 23:00–01:00, SR at 23:30 → buckets 23:00, 00:00, 01:00.
        Without the day-shift, end_time would be before start_time and the
        record would be incorrectly skipped.
        """
        event_type = EventType.get_from_desc("Class Time Block")
        late_slot, _ = Event.objects.get_or_create(
            program=self.program,
            event_type=event_type,
            start=datetime.datetime(2026, 3, 20, 23, 0, 0),
            end=datetime.datetime(2026, 3, 21, 1, 0, 0),
            short_description="Late Slot",
            description="23:00 03/20/2026",
        )
        night_section = (
            ClassSection.objects.filter(parent_class__parent_program=self.program)
            .order_by("id")
            .exclude(pk=self.section.pk)
            .first()
        )
        night_section.assign_meeting_times([late_slot])

        student = self.students[0]
        self._make_sr(student, datetime.datetime(2026, 3, 20, 23, 30, 0),
                      section=night_section)

        result = self.module.times_attending_class(self.program)

        self.assertUserInBuckets(student, [
            datetime.datetime(2026, 3, 20, 23, 0, 0),
            datetime.datetime(2026, 3, 21, 0, 0, 0),
            datetime.datetime(2026, 3, 21, 1, 0, 0),
        ], result)

    def test_normal_same_day_sr_produces_correct_buckets(self):
        """
        Confirms the handler's main while-loop path is stable for a normal
        same-day SR (section 09:00–11:00, SR at 09:30).

        Note: the handler contains a defensive guard clause
            if end_time < start_time: continue
        that is unreachable under the current date-replace logic (both
        start_time and end_time use the SR's own date, so end_time can only
        be < start_time when the cross-midnight day-shift applies, and that
        shift always resolves the inequality). This test documents the normal
        path and confirms no crash occurs.
        """
        student = self.students[0]
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 30, 0))

        result = self.module.times_attending_class(self.program)

        self.assertUserInBuckets(student, [
            datetime.datetime(2026, 3, 20, 9, 0, 0),
            datetime.datetime(2026, 3, 20, 10, 0, 0),
            datetime.datetime(2026, 3, 20, 11, 0, 0),
        ], result)


class TestTimesCheckedIn(_OnSiteAttendanceBase):
    """
    Regression tests for OnSiteAttendance.times_checked_in().

    Invariants under test:
      - Returns list; empty when no Records exist.
      - One entry per user (their minimum/earliest check-in time).
      - Result is sorted in ascending chronological order.
      - Records from a different program are excluded.
    """

    def test_no_records_returns_empty_list(self):
        """Empty program → empty list (not None, not {})."""
        result = self.module.times_checked_in(self.program)
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])

    def test_single_record_returns_that_timestamp(self):
        """One check-in record → list containing exactly that timestamp."""
        when = datetime.datetime(2026, 3, 20, 9, 5, 0)
        self._make_record(self.students[0], when)

        self.assertEqual(self.module.times_checked_in(self.program), [when])

    def test_uses_earliest_checkin_per_user(self):
        """Multiple records for one user → only the minimum time is kept."""
        student = self.students[0]
        earlier = datetime.datetime(2026, 3, 20, 9, 5, 0)
        later   = datetime.datetime(2026, 3, 20, 9, 30, 0)
        self._make_record(student, later)
        self._make_record(student, earlier)

        result = self.module.times_checked_in(self.program)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], earlier)

    def test_result_is_sorted_ascending(self):
        """Result must be chronologically sorted regardless of insertion order."""
        s0, s1, s2 = self.students
        self._make_record(s2, datetime.datetime(2026, 3, 20, 11, 0, 0))
        self._make_record(s0, datetime.datetime(2026, 3, 20, 9, 5, 0))
        self._make_record(s1, datetime.datetime(2026, 3, 20, 10, 0, 5))

        result = self.module.times_checked_in(self.program)
        self.assertEqual(result, sorted(result))

    def test_one_entry_per_user_regardless_of_record_count(self):
        """s0×2, s1×1, s2×3 records → exactly 3 entries in result."""
        s0, s1, s2 = self.students
        for t in [datetime.datetime(2026, 3, 20, 9, 5, 0),
                  datetime.datetime(2026, 3, 20, 9, 20, 0)]:
            self._make_record(s0, t)
        self._make_record(s1, datetime.datetime(2026, 3, 20, 10, 0, 0))
        for t in [datetime.datetime(2026, 3, 20, 10, 30, 0),
                  datetime.datetime(2026, 3, 20, 10, 45, 0),
                  datetime.datetime(2026, 3, 20, 11, 0, 0)]:
            self._make_record(s2, t)

        self.assertEqual(len(self.module.times_checked_in(self.program)), 3)

    def test_returns_correct_min_times_for_multiple_users(self):
        """End-to-end: each user's minimum time, sorted ascending."""
        s0, s1, s2 = self.students
        records = {
            s0: [datetime.datetime(2026, 3, 20, 9, 12, 30),
                 datetime.datetime(2026, 3, 20, 9, 5, 10)],
            s1: [datetime.datetime(2026, 3, 20, 10, 0, 5)],
            s2: [datetime.datetime(2026, 3, 20, 10, 59, 59),
                 datetime.datetime(2026, 3, 20, 11, 0, 0)],
        }
        for user, times in records.items():
            for t in times:
                self._make_record(user, t)

        expected = sorted(min(ts) for ts in records.values())
        self.assertEqual(self.module.times_checked_in(self.program), expected)

    def test_excludes_records_from_different_program(self):
        """Records for another program must not appear in self.program's result."""
        other = self._make_other_program(num_timeslots=1)
        Record.objects.create(
            event=self.attended_record_type,
            program=other.program,
            user=self.students[0],
            time=datetime.datetime(2026, 3, 20, 9, 0, 0),
        )

        self.assertEqual(
            self.module.times_checked_in(self.program), [],
            "Record from a different program leaked into times_checked_in().",
        )
