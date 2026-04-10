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

from esp.program.models import ClassSection, RegistrationType, StudentRegistration
from esp.program.modules.handlers.onsiteattendance import OnSiteAttendance
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class OnSiteAttendanceTest(ProgramFrameworkTest):
    """
    Regression tests for OnSiteAttendance.times_attending_class() and
    OnSiteAttendance.times_checked_in().

    Setup uses hour-aligned, zero-gap timeslots starting at 09:00 so that the
    handler's hour-bucket truncation (replace(minute=0, ...)) produces
    deterministic, easy-to-reason-about boundaries.

    Section layout (2 timeslots assigned in setUp):
        slot 0: 09:00 – 10:00
        slot 1: 10:00 – 11:00   <-- section end_time().end == 11:00

    This means times_attending_class() will count a student in every bucket
    from their sr.start_date hour up to and including the 11:00 bucket.
    """

    # ------------------------------------------------------------------ #
    # setUp / tearDown                                                     #
    # ------------------------------------------------------------------ #

    def setUp(self):
        super().setUp(
            num_timeslots=4,       # 09:00, 10:00, 11:00, 12:00
            timeslot_length=60,    # 60-minute slots → hour-aligned boundaries
            timeslot_gap=0,        # no gap → consecutive hours
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

        # Pick the first section and give it two consecutive hour-aligned slots
        # so section.end_time().end == 11:00 on 2026-03-20.
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
        self.section.assign_meeting_times(time_slots[:2])  # slots 0 & 1

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
    # Private helpers                                                      #
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

    def _bucket(self, dt):
        """Mirror the handler's hour-truncation logic."""
        return dt.replace(minute=0, second=0, microsecond=0)

    def _section_end_bucket(self, section=None):
        s = section or self.section
        return self._bucket(s.end_time().end)

    def _expected_buckets_for_sr(self, start_dt, section=None):
        """
        Return the list of hour buckets the handler will emit for a single SR
        whose start_date is start_dt, attending `section`.
        """
        start_bucket = self._bucket(start_dt)
        end_bucket = self._section_end_bucket(section)
        buckets = []
        t = start_bucket
        while t <= end_bucket:
            buckets.append(t)
            t += datetime.timedelta(hours=1)
        return buckets

    # ------------------------------------------------------------------ #
    # times_attending_class – basic correctness                           #
    # ------------------------------------------------------------------ #

    def test_empty_program_returns_empty_dict(self):
        """With no attendance SRs the result is an empty dict (not None, not [])."""
        result = self.module.times_attending_class(self.program)
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})

    def test_single_student_single_hour_bucket(self):
        """
        A student marked at 09:15 in a section ending at 11:00 appears in
        buckets 09:00, 10:00, and 11:00 – one entry per bucket, no extras.
        """
        student = self.students[0]
        when = datetime.datetime(2026, 3, 20, 9, 15, 0)
        self._make_sr(student, when)

        result = self.module.times_attending_class(self.program)

        expected = self._expected_buckets_for_sr(when)
        self.assertEqual(sorted(result.keys()), expected)
        for bucket in expected:
            self.assertEqual(
                result[bucket],
                [student],
                f"Expected exactly [student] in bucket {bucket!r}.",
            )

    def test_result_keys_are_chronologically_ordered(self):
        """
        The dict returned by times_attending_class() must have keys in
        ascending chronological order (the graph rendering depends on this).
        """
        s0, s1, s2 = self.students
        self._make_sr(s0, datetime.datetime(2026, 3, 20, 9, 5, 0))
        self._make_sr(s1, datetime.datetime(2026, 3, 20, 10, 5, 0))
        self._make_sr(s2, datetime.datetime(2026, 3, 20, 11, 5, 0))

        result = self.module.times_attending_class(self.program)
        keys = list(result.keys())
        self.assertEqual(keys, sorted(keys), "Result keys must be in ascending order.")

    def test_students_in_different_hour_buckets_are_grouped_correctly(self):
        """
        s0 marked at 09:15, s1 at 09:45, s2 at 10:05.
        Section ends at 11:00.

        Expected per bucket:
            09:00 → {s0, s1}
            10:00 → {s0, s1, s2}   (s0 & s1 carry forward each hour)
            11:00 → {s0, s1, s2}
        """
        s0, s1, s2 = self.students
        self._make_sr(s0, datetime.datetime(2026, 3, 20, 9, 15, 0))
        self._make_sr(s1, datetime.datetime(2026, 3, 20, 9, 45, 0))
        self._make_sr(s2, datetime.datetime(2026, 3, 20, 10, 5, 0))

        result = self.module.times_attending_class(self.program)

        b9  = datetime.datetime(2026, 3, 20, 9, 0, 0)
        b10 = datetime.datetime(2026, 3, 20, 10, 0, 0)
        b11 = datetime.datetime(2026, 3, 20, 11, 0, 0)

        self.assertIn(b9,  result)
        self.assertIn(b10, result)
        self.assertIn(b11, result)

        self.assertEqual({u.id for u in result[b9]},  {s0.id, s1.id})
        self.assertEqual({u.id for u in result[b10]}, {s0.id, s1.id, s2.id})
        self.assertEqual({u.id for u in result[b11]}, {s0.id, s1.id, s2.id})

    # ------------------------------------------------------------------ #
    # times_attending_class – duplicate-prevention                        #
    # ------------------------------------------------------------------ #

    def test_same_student_marked_twice_in_same_hour_counted_once(self):
        """
        Two SRs for the same student within the same hour bucket must not
        inflate the count for that bucket.  This is the core deduplication
        invariant of the handler.
        """
        student = self.students[0]
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 10, 0))
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 55, 0))

        result = self.module.times_attending_class(self.program)

        for bucket, users in result.items():
            user_ids = [u.id for u in users]
            self.assertEqual(
                len(user_ids),
                len(set(user_ids)),
                f"Duplicate user detected in bucket {bucket!r}: {user_ids}",
            )
            self.assertLessEqual(
                user_ids.count(student.id),
                1,
                f"Student appears more than once in bucket {bucket!r}.",
            )

    def test_same_student_marked_in_different_hours_no_cross_bucket_duplication(self):
        """
        Two SRs for the same student in *different* hour buckets: the student
        should appear in every bucket from the earlier SR onward (carry-forward
        logic), but still only once per bucket.
        """
        student = self.students[0]
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 5, 0))
        self._make_sr(student, datetime.datetime(2026, 3, 20, 10, 5, 0))

        result = self.module.times_attending_class(self.program)

        for bucket, users in result.items():
            user_ids = [u.id for u in users]
            self.assertEqual(
                len(user_ids),
                len(set(user_ids)),
                f"Duplicate user in bucket {bucket!r}.",
            )

    # ------------------------------------------------------------------ #
    # times_attending_class – section without meeting times is excluded   #
    # ------------------------------------------------------------------ #

    def test_sr_for_unscheduled_section_is_excluded(self):
        """
        The handler filters section__meeting_times__isnull=False.
        An SR whose section has no meeting times must not appear in the result.
        """
        # Create a second section and strip its meeting times.
        unscheduled_section = (
            ClassSection.objects.filter(parent_class__parent_program=self.program)
            .order_by("id")
            .last()
        )
        unscheduled_section.clear_meeting_times()

        student = self.students[0]
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 0, 0),
                      section=unscheduled_section)

        result = self.module.times_attending_class(self.program)

        # The student should not appear in any bucket.
        for bucket, users in result.items():
            self.assertNotIn(
                student,
                users,
                f"Student from unscheduled section appeared in bucket {bucket!r}.",
            )

    # ------------------------------------------------------------------ #
    # times_attending_class – program isolation                           #
    # ------------------------------------------------------------------ #

    def test_sr_from_different_program_is_excluded(self):
        """
        SRs belonging to a different program must never bleed into the result
        for self.program.
        """
        # Spin up a second minimal program.
        from esp.program.tests import ProgramFrameworkTest as PFT
        other = PFT()
        other.setUp(
            num_timeslots=2,
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
            program_type="OtherProgram",
            program_instance_name="2222_Fall",
            program_instance_label="Fall 2222",
            start_time=datetime.datetime(2026, 3, 20, 9, 0, 0),
        )
        other_section = (
            ClassSection.objects.filter(
                parent_class__parent_program=other.program
            )
            .order_by("id")
            .first()
        )
        other_ts = list(other.program.getTimeSlots().order_by("start"))
        other_section.assign_meeting_times(other_ts[:2])

        # Register one of *our* students in the other program's section.
        shared_student = self.students[0]
        StudentRegistration.objects.create(
            user=shared_student,
            section=other_section,
            relationship=self.attended_sr_type,
            start_date=datetime.datetime(2026, 3, 20, 9, 0, 0),
        )

        result = self.module.times_attending_class(self.program)

        # self.program has no SRs → result must be empty.
        self.assertEqual(
            result,
            {},
            "SR from a different program leaked into times_attending_class().",
        )

    # ------------------------------------------------------------------ #
    # times_attending_class – cross-midnight edge case                    #
    # ------------------------------------------------------------------ #

    def test_cross_midnight_class_end_time_shifted_forward_one_day(self):
        """
        Regression for the cross-midnight branch in times_attending_class():

            if section_end_dt.time() < start_time.time():
                end_time += timedelta(days=1)

        A section whose end time-of-day is earlier than the student's
        attendance start time-of-day (e.g. class runs 23:00–01:00 and the
        student is marked at 23:30) must have its end_time shifted forward
        by one day so the while-loop terminates correctly.

        We simulate this by giving the section a timeslot that ends at 01:00
        and creating an SR with start_date at 23:30 on the previous day.
        """
        from esp.cal.models import Event, EventType

        event_type = EventType.get_from_desc("Class Time Block")
        # Slot: 2026-03-20 23:00 – 2026-03-21 01:00
        late_slot, _ = Event.objects.get_or_create(
            program=self.program,
            event_type=event_type,
            start=datetime.datetime(2026, 3, 20, 23, 0, 0),
            end=datetime.datetime(2026, 3, 21, 1, 0, 0),
            short_description="Late Slot",
            description="23:00 03/20/2026",
        )

        # Use a fresh section so we don't disturb the main setUp section.
        night_section = (
            ClassSection.objects.filter(parent_class__parent_program=self.program)
            .order_by("id")
            .last()
        )
        night_section.assign_meeting_times([late_slot])

        student = self.students[0]
        # SR at 23:30 on 2026-03-20; section ends at 01:00 on 2026-03-21.
        sr_time = datetime.datetime(2026, 3, 20, 23, 30, 0)
        self._make_sr(student, sr_time, section=night_section)

        result = self.module.times_attending_class(self.program)

        # Expected buckets: 23:00 on 3/20 and 00:00 on 3/21 and 01:00 on 3/21.
        b_2300 = datetime.datetime(2026, 3, 20, 23, 0, 0)
        b_0000 = datetime.datetime(2026, 3, 21, 0, 0, 0)
        b_0100 = datetime.datetime(2026, 3, 21, 1, 0, 0)

        self.assertIn(b_2300, result, "Missing 23:00 bucket for cross-midnight class.")
        self.assertIn(b_0000, result, "Missing 00:00 bucket for cross-midnight class.")
        self.assertIn(b_0100, result, "Missing 01:00 bucket for cross-midnight class.")
        self.assertIn(student, result[b_2300])
        self.assertIn(student, result[b_0000])
        self.assertIn(student, result[b_0100])

    def test_invalid_end_time_after_adjustment_skips_record(self):
        """
        Regression for the guard clause:

            if end_time < start_time:   # after the cross-midnight shift attempt
                continue

        If the section's end time-of-day equals the start time-of-day (a
        zero-duration edge case after truncation), the record must be silently
        skipped rather than causing an infinite loop or error.

        We test this by creating an SR whose start_date hour exactly equals
        the section's end_time hour on the same day, but the section end is
        strictly before the SR start (i.e. end_time < start_time and
        section_end_dt.time() >= start_time.time() so no day-shift occurs).
        """
        from esp.cal.models import Event, EventType

        event_type = EventType.get_from_desc("Class Time Block")
        # Section ends at 08:00; SR is at 09:00 → end_time < start_time,
        # and section_end_dt.time() (08:00) is NOT < start_time.time() (09:00),
        # so no day-shift → the record must be skipped.
        early_slot, _ = Event.objects.get_or_create(
            program=self.program,
            event_type=event_type,
            start=datetime.datetime(2026, 3, 20, 7, 0, 0),
            end=datetime.datetime(2026, 3, 20, 8, 0, 0),
            short_description="Early Slot",
            description="07:00 03/20/2026",
        )
        early_section = (
            ClassSection.objects.filter(parent_class__parent_program=self.program)
            .order_by("id")
            .last()
        )
        early_section.assign_meeting_times([early_slot])

        student = self.students[0]
        # SR at 09:00 – section already ended at 08:00.
        self._make_sr(student, datetime.datetime(2026, 3, 20, 9, 0, 0),
                      section=early_section)

        # Should not raise; the record must be silently skipped.
        result = self.module.times_attending_class(self.program)

        for bucket, users in result.items():
            self.assertNotIn(
                student,
                users,
                f"Skipped record unexpectedly appeared in bucket {bucket!r}.",
            )

    # ------------------------------------------------------------------ #
    # times_checked_in – basic correctness                                #
    # ------------------------------------------------------------------ #

    def test_times_checked_in_empty_returns_empty_list(self):
        """With no Records the result is an empty list (not None, not {})."""
        result = self.module.times_checked_in(self.program)
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])

    def test_times_checked_in_single_student_single_record(self):
        """A single check-in record returns a list with exactly that timestamp."""
        student = self.students[0]
        when = datetime.datetime(2026, 3, 20, 9, 5, 0)
        self._make_record(student, when)

        result = self.module.times_checked_in(self.program)
        self.assertEqual(result, [when])

    def test_times_checked_in_returns_min_time_per_user(self):
        """
        When a student checks in multiple times, only their *earliest* check-in
        time is included in the result (one entry per user).
        """
        student = self.students[0]
        earlier = datetime.datetime(2026, 3, 20, 9, 5, 0)
        later   = datetime.datetime(2026, 3, 20, 9, 30, 0)
        self._make_record(student, later)
        self._make_record(student, earlier)

        result = self.module.times_checked_in(self.program)

        self.assertEqual(len(result), 1, "Expected exactly one entry per user.")
        self.assertEqual(result[0], earlier, "Expected the earliest check-in time.")

    def test_times_checked_in_result_is_sorted_ascending(self):
        """
        The list returned by times_checked_in() must be in ascending
        chronological order regardless of insertion order.
        """
        s0, s1, s2 = self.students
        self._make_record(s2, datetime.datetime(2026, 3, 20, 11, 0, 0))
        self._make_record(s0, datetime.datetime(2026, 3, 20, 9, 5, 0))
        self._make_record(s1, datetime.datetime(2026, 3, 20, 10, 0, 5))

        result = self.module.times_checked_in(self.program)

        self.assertEqual(result, sorted(result), "Result must be chronologically sorted.")

    def test_times_checked_in_one_entry_per_user(self):
        """
        Even with multiple records per user, the result length equals the
        number of distinct users who checked in.
        """
        s0, s1, s2 = self.students
        # s0: two records; s1: one record; s2: three records
        for t in [datetime.datetime(2026, 3, 20, 9, 5, 0),
                  datetime.datetime(2026, 3, 20, 9, 20, 0)]:
            self._make_record(s0, t)
        self._make_record(s1, datetime.datetime(2026, 3, 20, 10, 0, 0))
        for t in [datetime.datetime(2026, 3, 20, 10, 30, 0),
                  datetime.datetime(2026, 3, 20, 10, 45, 0),
                  datetime.datetime(2026, 3, 20, 11, 0, 0)]:
            self._make_record(s2, t)

        result = self.module.times_checked_in(self.program)

        self.assertEqual(len(result), 3, "Expected one entry per distinct user.")

    def test_times_checked_in_correct_min_times_for_multiple_users(self):
        """
        End-to-end: three students with multiple records each.
        Result must contain each student's minimum check-in time, sorted.
        """
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

        result = self.module.times_checked_in(self.program)

        expected = sorted(min(ts) for ts in records.values())
        self.assertEqual(result, expected)

    # ------------------------------------------------------------------ #
    # times_checked_in – program isolation                                #
    # ------------------------------------------------------------------ #

    def test_times_checked_in_excludes_records_from_other_program(self):
        """
        Records belonging to a different program must not appear in the result
        for self.program.
        """
        from esp.program.tests import ProgramFrameworkTest as PFT
        other = PFT()
        other.setUp(
            num_timeslots=1,
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
            program_type="OtherProgram",
            program_instance_name="2222_Fall",
            program_instance_label="Fall 2222",
            start_time=datetime.datetime(2026, 3, 20, 9, 0, 0),
        )

        shared_student = self.students[0]
        Record.objects.create(
            event=self.attended_record_type,
            program=other.program,
            user=shared_student,
            time=datetime.datetime(2026, 3, 20, 9, 0, 0),
        )

        result = self.module.times_checked_in(self.program)

        self.assertEqual(
            result,
            [],
            "Record from a different program leaked into times_checked_in().",
        )
