"""Tests for cached functions that read m2m data.

An m2m edit does not fire post_save on either end, so a cache that reads an m2m
relation needs an explicit depend_on_m2m.  Each test below drives a real m2m
edit and asserts the cache noticed.
"""

from datetime import datetime, timedelta

from esp.cal.models import Event
from esp.program.models import ClassSubject, ProgramModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser


class MeetingTimesCacheDepTest(ProgramFrameworkTest):
    """meeting_times feeds getFirstClassTime and popular_classes."""

    def setUp(self):
        super().setUp(num_students=1, num_teachers=1, classes_per_teacher=1,
                      sections_per_class=1)
        self.student = self.students[0]
        self.section = ClassSubject.objects.filter(
            parent_program=self.program).first().sections.first()
        self.spare_slot = Event.objects.create(
            program=self.program, event_type=self.event_type,
            start=datetime(2222, 7, 9, 9, 0),
            end=datetime(2222, 7, 9, 9, 0) + timedelta(hours=1),
            name='spare slot', short_description='spare',
            description='spare slot for m2m cache tests')

    def enroll(self):
        self.section.preregister_student(self.student, overridefull=True)

    def test_getFirstClassTime_follows_rescheduling(self):
        """getFirstClassTime reads the section's meeting_times, so a reschedule
        must change its answer rather than serving the cached time."""
        self.section.meeting_times.clear()
        self.section.meeting_times.add(self.timeslots[1])
        self.enroll()

        first = self.student.getFirstClassTime(self.program)
        self.assertEqual(first, self.timeslots[1])

        #   Move the section earlier; the cached answer must not survive.
        self.section.meeting_times.clear()
        self.section.meeting_times.add(self.timeslots[0])

        self.assertEqual(self.student.getFirstClassTime(self.program),
                         self.timeslots[0],
                         "getFirstClassTime served a stale meeting time")

    def test_getFirstClassTime_follows_added_time(self):
        self.section.meeting_times.clear()
        self.section.meeting_times.add(self.timeslots[2])
        self.enroll()
        self.assertEqual(self.student.getFirstClassTime(self.program),
                         self.timeslots[2])

        self.section.meeting_times.add(self.timeslots[0])
        self.assertEqual(self.student.getFirstClassTime(self.program),
                         self.timeslots[0],
                         "getFirstClassTime ignored a newly added earlier time")


class ProgramModulesCacheDepTest(ProgramFrameworkTest):
    """program_modules feeds getModules_cached."""

    def setUp(self):
        super().setUp(num_students=0, num_teachers=0, classes_per_teacher=0)

    def test_getModules_cached_follows_module_changes(self):
        before = len(self.program.getModules_cached())
        self.assertGreater(before, 0)

        removed = self.program.program_modules.first()
        self.program.program_modules.remove(removed)

        self.assertEqual(len(self.program.getModules_cached()), before - 1,
                         "getModules_cached served a stale module list")

    def test_getModules_cached_follows_module_addition(self):
        removed = self.program.program_modules.first()
        self.program.program_modules.remove(removed)
        after_removal = len(self.program.getModules_cached())

        self.program.program_modules.add(removed)
        self.assertEqual(len(self.program.getModules_cached()), after_removal + 1,
                         "getModules_cached ignored a re-added module")


class AllowableClassSizeRangesCacheDepTest(ProgramFrameworkTest):
    """allowable_class_size_ranges feeds ClassSection.capacity."""

    def setUp(self):
        super().setUp(num_students=0, num_teachers=1, classes_per_teacher=1,
                      sections_per_class=1)
        self.cls = ClassSubject.objects.filter(parent_program=self.program).first()
        self.section = self.cls.sections.first()
        self.section.meeting_times.add(self.timeslots[0])

    def test_capacity_cache_is_dropped_when_size_ranges_change(self):
        """capacity reads parent_class.allowable_class_size_ranges, so editing
        that m2m must drop the cached value.  Asserted on the cache directly
        because the resulting number depends on room assignments."""
        from esp.program.models.class_ import ClassSizeRange

        self.section.capacity                                   # warm
        self.assertIsNotNone(self.section._get_capacity(cache_only=True),
                             "capacity should be cached after first access")

        rng = ClassSizeRange.objects.create(range_min=1, range_max=99,
                                            program=self.program)
        self.cls.allowable_class_size_ranges.add(rng)

        self.assertIsNone(self.section._get_capacity(cache_only=True),
                          "capacity cache survived a size-range change")


class PopularClassesCacheDepTest(ProgramFrameworkTest):
    """meeting_times feeds BigBoardModule.popular_classes."""

    def setUp(self):
        super().setUp(num_students=1, num_teachers=1, classes_per_teacher=1,
                      sections_per_class=1)
        self.module = self.program.getModule('BigBoardModule')
        self.section = ClassSubject.objects.filter(
            parent_program=self.program).first().sections.first()

    def test_popular_classes_cache_is_dropped_when_rescheduled(self):
        """popular_classes includes each section's meeting times."""
        self.module.popular_classes(self.program)               # warm
        self.assertIsNotNone(
            self.module.popular_classes(self.program, cache_only=True),
            "popular_classes should be cached after first call")

        self.section.meeting_times.add(self.timeslots[0])

        self.assertIsNone(
            self.module.popular_classes(self.program, cache_only=True),
            "popular_classes cache survived a reschedule")
