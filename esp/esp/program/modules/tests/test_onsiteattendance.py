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
from collections import Counter

from esp.program.models import ClassSection, RegistrationType, StudentRegistration
from esp.program.modules.handlers.onsiteattendance import OnSiteAttendance
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record, RecordType


class OnSiteAttendanceTest(ProgramFrameworkTest):
    """
    Regression tests for OnSiteAttendance.times_attending_class() and
    OnSiteAttendance.times_checked_in().

    These tests validate real data aggregation by hour buckets, ordering, and
    duplicate prevention.
    """

    def setUp(self):
        # Use hour-aligned timeslots so the handler's replace(minute=0, ...)
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
        # section.end_time().end lands on an hour boundary.
        time_slots = list(self.program.getTimeSlots().order_by("start"))
        self.section.assign_meeting_times(time_slots[:2])

    def tearDown(self):
        StudentRegistration.objects.filter(
            section=self.section, relationship=self.attended_sr_type
        ).delete()
        Record.objects.filter(program=self.program, event=self.attended_record_type).delete()
        super().tearDown()

    # --- helpers ---

    def _make_attended_registration(self, student, when):
        """Create a real attendance SR row so times_attending_class() uses the same queries as production."""
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
        """Truncate to the handler's hour-bucket granularity."""
        return dt.replace(minute=0, second=0, microsecond=0)

    def _section_end_bucket(self):
        """Compute the end hour bucket for this section."""
        return self._bucket_hour(self.section.end_time().end)

    def _expected_attending_buckets(self, attendance_when_by_user):
        """
        Given real attendance start datetimes per user, compute:
          - the expected hour buckets (chronological)
          - each user's earliest bucket start

        Handler behavior: for each attendance SR, it starts counting at
        sr.start_date hour-truncation and counts the student each hour until
        the end bucket, preventing duplicate counting per student per bucket.
        """
        user_start_buckets = {
            user: min(self._bucket_hour(dt) for dt in when_list)
            for user, when_list in attendance_when_by_user.items()
        }
        min_bucket = min(user_start_buckets.values())
        end_bucket = self._section_end_bucket()

        buckets = []
        t = min_bucket
        while t <= end_bucket:
            buckets.append(t)
            t += datetime.timedelta(hours=1)
        return buckets, user_start_buckets

    # --- tests ---

    def test_times_attending_class_groups_and_orders_hour_buckets(self):
        """times_attending_class() groups attendees into chronological hour buckets."""
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

    def test_times_attending_class_no_duplicate_per_hour_bucket(self):
        """A student marked twice within the same hour is counted only once per bucket."""
        student = self.students[0]
        when_list = [
            datetime.datetime(2026, 3, 20, 9, 10, 0),
            datetime.datetime(2026, 3, 20, 9, 55, 0),
        ]
        for when in when_list:
            self._make_attended_registration(student, when)

        result = self.module.times_attending_class(self.program)
        expected_buckets, _ = self._expected_attending_buckets({student: when_list})

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

    def test_times_checked_in_returns_min_time_per_user_ordered(self):
        """times_checked_in() returns one entry per user (their earliest check-in), sorted."""
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

        # Validate hour-bucket grouping.
        bucket_counts = Counter(self._bucket_hour(t) for t in result)
        expected_bucket_counts = Counter(self._bucket_hour(t) for t in expected_min_times)
        self.assertEqual(bucket_counts, expected_bucket_counts)
        self.assertEqual(list(bucket_counts.keys()), sorted(bucket_counts.keys()))

    def test_times_empty_data(self):
        """With no attendance data, both methods return empty results."""
        attending = self.module.times_attending_class(self.program)
        total_attendees = sum(len(users) for users in attending.values())
        self.assertEqual(total_attendees, 0)

        checked_in = self.module.times_checked_in(self.program)
        self.assertEqual(len(checked_in), 0)
