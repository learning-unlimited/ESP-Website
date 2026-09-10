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


class ShirtInfoAndModNumsCacheDepTest(ProgramFrameworkTest):
    """getShirtInfo and mod_nums read prog.teachers(), which TeacherClassRegModule
    builds from the ClassSubject.teachers m2m and section statuses, and mod_nums
    additionally aggregates Count('meeting_times')."""

    def setUp(self):
        super().setUp(num_students=0, num_teachers=2, classes_per_teacher=1,
                      sections_per_class=1)
        self.cls = ClassSubject.objects.filter(parent_program=self.program).first()
        self.section = self.cls.sections.first()
        self.json_module = self.program.getModule('JSONDataModule')

    def test_getShirtInfo_follows_teacher_changes(self):
        self.program.getShirtInfo()
        self.assertIsNotNone(self.program.getShirtInfo(cache_only=True))

        self.cls.makeTeacher(self.teachers[1])

        self.assertIsNone(self.program.getShirtInfo(cache_only=True),
                          "adding a teacher must invalidate getShirtInfo")

    def test_getShirtInfo_follows_section_changes(self):
        self.program.getShirtInfo()
        self.assertIsNotNone(self.program.getShirtInfo(cache_only=True))

        self.section.status = 5
        self.section.save()

        self.assertIsNone(self.program.getShirtInfo(cache_only=True),
                          "a section status change must invalidate getShirtInfo")

    def test_mod_nums_follows_rescheduling(self):
        from esp.program.modules.handlers.jsondatamodule import JSONDataModule
        JSONDataModule.mod_nums(self.program)
        self.assertIsNotNone(JSONDataModule.mod_nums(self.program, cache_only=True))

        self.section.meeting_times.add(self.timeslots[0])

        self.assertIsNone(JSONDataModule.mod_nums(self.program, cache_only=True),
                          "rescheduling must invalidate mod_nums")


class ModeratorCacheDepTest(ProgramFrameworkTest):
    """Moderator-facing caches read m2m data that post_save cannot see."""

    def setUp(self):
        super().setUp(num_students=0, num_teachers=1, classes_per_teacher=1,
                      sections_per_class=1)
        self.moderator = self.teachers[0]
        self.section = ClassSubject.objects.filter(
            parent_program=self.program).first().sections.first()
        self.section.moderators.add(self.moderator)

    def test_moderating_sections_follows_rescheduling(self):
        """Results are ordered by Min('meeting_times__start')."""
        self.moderator.getModeratingSectionsFromProgram(self.program)
        self.assertIsNotNone(
            self.moderator.getModeratingSectionsFromProgram(self.program, cache_only=True))

        self.section.meeting_times.add(self.timeslots[0])

        self.assertIsNone(
            self.moderator.getModeratingSectionsFromProgram(self.program, cache_only=True),
            "rescheduling must invalidate the moderating-sections cache")

    def test_moderators_json_follows_category_changes(self):
        """The payload includes rec.class_categories, an m2m on ModeratorRecord."""
        from esp.program.models import ModeratorRecord
        from esp.program.modules.handlers.jsondatamodule import JSONDataModule

        rec = ModeratorRecord.objects.create(user=self.moderator, program=self.program,
                                             will_moderate=True, num_slots=1)
        JSONDataModule.moderators.method.cached_function(self.program)
        self.assertIsNotNone(
            JSONDataModule.moderators.method.cached_function(self.program, cache_only=True))

        rec.class_categories.add(self.categories[0])

        self.assertIsNone(
            JSONDataModule.moderators.method.cached_function(self.program, cache_only=True),
            "a moderator category change must invalidate the moderators payload")


class ModeratorsAvailabilityScopeTest(ProgramFrameworkTest):
    """moderators(prog) reads each moderator's availability; that dependency
    used to be a wildcard, undoing the scoping of the other three."""

    def setUp(self):
        super().setUp(num_students=0, num_teachers=1, classes_per_teacher=1,
                      sections_per_class=1)
        from esp.tests.factories import make_program
        self.program_b = make_program(
            instance_name='2225_Summer', instance_label='Summer 2225',
            categories=self.categories, admins=self.admins,
            modules=self.settings['modules'])

    def test_availability_change_spares_the_other_program(self):
        from esp.program.modules.handlers.jsondatamodule import JSONDataModule
        from esp.users.models import UserAvailability
        from django.contrib.auth.models import Group

        cf = JSONDataModule.moderators.method.cached_function
        cf(self.program); cf(self.program_b)
        self.assertIsNotNone(cf(self.program, cache_only=True))
        self.assertIsNotNone(cf(self.program_b, cache_only=True))

        UserAvailability.objects.create(
            user=self.teachers[0], event=self.timeslots[0],
            role=Group.objects.get_or_create(name='Teacher')[0])

        self.assertIsNone(cf(self.program, cache_only=True),
                          "program A's moderators payload should be invalidated")
        self.assertIsNotNone(cf(self.program_b, cache_only=True),
                             "program B's moderators payload should survive")
