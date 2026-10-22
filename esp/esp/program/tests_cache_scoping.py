"""Tests that per-program caches are not dumped wholesale by unrelated writes.

Each test warms the cache for two independent programs, writes to one, and
asserts the other survives.  Paired with an assertion that the written-to
program *was* invalidated, so over-scoping fails too.
"""

from datetime import datetime, timedelta

from esp.cal.models import Event
from esp.program.models import ClassSubject
from esp.program.modules.handlers.jsondatamodule import JSONDataModule
from esp.program.tests import ProgramFrameworkTest
from esp.tests.factories import make_class, make_program


class TwoProgramCacheTest(ProgramFrameworkTest):
    def setUp(self, **kwargs):
        kwargs.setdefault('num_students', 0)
        kwargs.setdefault('num_teachers', 1)
        kwargs.setdefault('classes_per_teacher', 1)
        kwargs.setdefault('sections_per_class', 1)
        super().setUp(**kwargs)
        self.program_b = make_program(
            instance_name='2224_Summer', instance_label='Summer 2224',
            categories=self.categories, admins=self.admins,
            modules=self.settings['modules'],
        )
        self.class_b = make_class(program=self.program_b, teacher=self.teachers[0],
                                  title='B class', category=self.categories[0],
                                  sections=1, accept=True)

    def a_class_in(self, program):
        return ClassSubject.objects.filter(parent_program=program).first()


class GetFullClassesPrettyScopeTest(TwoProgramCacheTest):
    """getFullClasses_pretty(self, program) was dumped for every user and every
    program whenever any ClassSubject was saved."""

    def cached(self, program):
        return self.teachers[0].getFullClasses_pretty(program, cache_only=True)

    def test_editing_one_program_spares_the_other(self):
        self.teachers[0].getFullClasses_pretty(self.program)
        self.teachers[0].getFullClasses_pretty(self.program_b)
        self.assertIsNotNone(self.cached(self.program))
        self.assertIsNotNone(self.cached(self.program_b))

        cls = self.a_class_in(self.program)
        cls.title = 'Retitled'
        cls.save()

        self.assertIsNone(self.cached(self.program),
                          "the edited program's entry should be invalidated")
        self.assertIsNotNone(self.cached(self.program_b),
                             "an unrelated program's entry should survive")

    def test_adding_a_teacher_still_invalidates(self):
        """The old wildcard covered class edits but not teacher m2m edits."""
        self.teachers[0].getFullClasses_pretty(self.program)
        self.assertIsNotNone(self.cached(self.program))

        self.a_class_in(self.program).makeTeacher(self.teachers[0])
        #   re-adding is a no-op for the relation, so use a real change
        self.a_class_in(self.program).removeTeacher(self.teachers[0])
        self.assertIsNone(self.cached(self.program),
                          "a teacher change must invalidate the entry")


class TimeslotsJsonScopeTest(TwoProgramCacheTest):
    """jsondatamodule.timeslots(prog) depended on cal.Event globally."""

    def cached(self, program):
        return JSONDataModule.timeslots.cached_function(program, cache_only=True)

    def test_event_change_spares_the_other_program(self):
        JSONDataModule.timeslots.cached_function(self.program)
        JSONDataModule.timeslots.cached_function(self.program_b)
        self.assertIsNotNone(self.cached(self.program))
        self.assertIsNotNone(self.cached(self.program_b))

        #   A new timeslot in program A only.
        Event.objects.create(
            program=self.program, event_type=self.event_type,
            start=datetime(2222, 7, 10, 9, 0),
            end=datetime(2222, 7, 10, 10, 0),
            name='A extra slot', short_description='extra',
            description='extra slot in program A')

        self.assertIsNone(self.cached(self.program),
                          "program A's timeslots should be invalidated")
        self.assertIsNotNone(self.cached(self.program_b),
                             "program B's timeslots should survive")

    def test_program_less_event_still_invalidates_everything(self):
        """Event.program is nullable; those fall back to a full dump."""
        JSONDataModule.timeslots.cached_function(self.program)
        JSONDataModule.timeslots.cached_function(self.program_b)

        Event.objects.create(
            program=None, event_type=self.event_type,
            start=datetime(2222, 7, 11, 9, 0),
            end=datetime(2222, 7, 11, 10, 0),
            name='global slot', short_description='global',
            description='event with no program')

        self.assertIsNone(self.cached(self.program))
        self.assertIsNone(self.cached(self.program_b))


class AjaxLunchTimeslotsScopeTest(TwoProgramCacheTest):
    """ajax_lunch_timeslots_cached(prog) depended on Event, ClassSection,
    ClassSubject and ClassCategories globally."""

    def setUp(self):
        super().setUp()
        self.mod_a = self.program.getModule('AJAXSchedulingModule')
        self.mod_b = self.program_b.getModule('AJAXSchedulingModule')

    def test_class_edit_spares_the_other_program(self):
        self.mod_a.ajax_lunch_timeslots_cached(self.program)
        self.mod_b.ajax_lunch_timeslots_cached(self.program_b)
        self.assertIsNotNone(
            self.mod_a.ajax_lunch_timeslots_cached(self.program, cache_only=True))
        self.assertIsNotNone(
            self.mod_b.ajax_lunch_timeslots_cached(self.program_b, cache_only=True))

        cls = self.a_class_in(self.program)
        cls.title = 'Retitled again'
        cls.save()

        self.assertIsNone(
            self.mod_a.ajax_lunch_timeslots_cached(self.program, cache_only=True),
            "program A's lunch timeslots should be invalidated")
        self.assertIsNotNone(
            self.mod_b.ajax_lunch_timeslots_cached(self.program_b, cache_only=True),
            "program B's lunch timeslots should survive")


class TokenBackedScopingTest(TwoProgramCacheTest):
    """Caches whose key_sets name only some of their parameters need a matching
    token; without one argcache falls back to dumping the whole cache, so the
    key_set is decorative.  These assert the tokens are doing their job."""

    def setUp(self):
        super().setUp(num_students=1)
        self.teacher = self.teachers[0]
        self.class_b.makeTeacher(self.teacher)

    def test_getTaughtClassesFromProgram_is_scoped_by_program(self):
        self.teacher.getTaughtClassesFromProgram(self.program)
        self.teacher.getTaughtClassesFromProgram(self.program_b)
        self.assertIsNotNone(
            self.teacher.getTaughtClassesFromProgram(self.program, cache_only=True))
        self.assertIsNotNone(
            self.teacher.getTaughtClassesFromProgram(self.program_b, cache_only=True))

        cls = self.a_class_in(self.program)
        cls.title = 'Retitled for scoping'
        cls.save()

        self.assertIsNone(
            self.teacher.getTaughtClassesFromProgram(self.program, cache_only=True),
            "the edited program's entry should be invalidated")
        self.assertIsNotNone(
            self.teacher.getTaughtClassesFromProgram(self.program_b, cache_only=True),
            "an unrelated program's entry should survive")

    def test_getFirstClassTime_is_scoped_by_program(self):
        student = self.students[0]
        sec_a = self.a_class_in(self.program).sections.first()
        sec_b = self.class_b.sections.first()
        sec_a.meeting_times.add(self.timeslots[0])
        #   B needs a meeting time too, or getFirstClassTime returns None there
        #   and a cached None is indistinguishable from a cache miss.
        sec_b.meeting_times.add(self.program_b.getTimeSlots()[0])
        sec_a.preregister_student(student, overridefull=True)
        sec_b.preregister_student(student, overridefull=True)

        student.getFirstClassTime(self.program)
        student.getFirstClassTime(self.program_b)
        self.assertIsNotNone(student.getFirstClassTime(self.program, cache_only=True))
        self.assertIsNotNone(student.getFirstClassTime(self.program_b, cache_only=True))

        #   Reschedule in program A only.
        sec_a.meeting_times.add(self.timeslots[1])

        self.assertIsNone(student.getFirstClassTime(self.program, cache_only=True),
                          "program A's entry should be invalidated")
        self.assertIsNotNone(student.getFirstClassTime(self.program_b, cache_only=True),
                             "program B's entry should survive")


class FullClassesEnrolmentDepTest(TwoProgramCacheTest):
    """getFullClasses_pretty calls is_nearly_full(), which compares
    num_students() against capacity scaled by the nearly_full_threshold tag.
    None of those were covered by its class-level dependencies."""

    def setUp(self):
        super().setUp(num_students=2)
        self.teacher = self.teachers[0]
        self.section = self.a_class_in(self.program).sections.first()
        self.section.meeting_times.add(self.timeslots[0])

    def cached(self, program):
        return self.teacher.getFullClasses_pretty(program, cache_only=True)

    def test_enrolment_invalidates(self):
        self.teacher.getFullClasses_pretty(self.program)
        self.assertIsNotNone(self.cached(self.program))

        self.section.preregister_student(self.students[0], overridefull=True)

        self.assertIsNone(self.cached(self.program),
                          "enrolling a student must invalidate the entry")

    def test_enrolment_in_one_program_spares_the_other(self):
        self.teacher.getFullClasses_pretty(self.program)
        self.teacher.getFullClasses_pretty(self.program_b)
        self.assertIsNotNone(self.cached(self.program_b))

        self.section.preregister_student(self.students[0], overridefull=True)

        self.assertIsNone(self.cached(self.program))
        self.assertIsNotNone(self.cached(self.program_b),
                             "an unrelated program's entry should survive")

    def test_capacity_change_invalidates(self):
        self.teacher.getFullClasses_pretty(self.program)
        self.assertIsNotNone(self.cached(self.program))

        self.section.max_class_capacity = (self.section.max_class_capacity or 0) + 5
        self.section.save()

        self.assertIsNone(self.cached(self.program),
                          "a capacity change must invalidate the entry")


class TagCacheScopeTest(ProgramFrameworkTest):
    """_getTag(cls, key, default, target) is keyed by (key, target) but had no
    matching token, so any tag write dumped every cached tag lookup."""

    def setUp(self):
        super().setUp(num_students=0, num_teachers=0, classes_per_teacher=0)
        from esp.tagdict.models import Tag
        self.Tag = Tag
        Tag.setTag('cache_scope_a', value='1')
        Tag.setTag('cache_scope_b', value='1')

    def cached(self, key):
        return self.Tag._getTag(key, cache_only=True)

    def test_writing_one_tag_spares_other_tags(self):
        self.Tag._getTag('cache_scope_a')
        self.Tag._getTag('cache_scope_b')
        self.assertIsNotNone(self.cached('cache_scope_a'))
        self.assertIsNotNone(self.cached('cache_scope_b'))

        self.Tag.setTag('cache_scope_a', value='2')

        self.assertIsNone(self.cached('cache_scope_a'),
                          "the written tag should be invalidated")
        self.assertIsNotNone(self.cached('cache_scope_b'),
                             "an unrelated tag's lookup should survive")


class NumStudentsCacheScopeTest(ProgramFrameworkTest):
    """num_students(self, verbs) is keyed by section; without a token any
    registration dumped the count for every section."""

    def setUp(self):
        super().setUp(num_students=1, num_teachers=2, classes_per_teacher=1,
                      sections_per_class=1)
        secs = [c.sections.first() for c in
                ClassSubject.objects.filter(parent_program=self.program)]
        self.sec_a, self.sec_b = secs[0], secs[1]

    def test_enrolling_in_one_section_spares_the_other(self):
        self.sec_a.num_students()
        self.sec_b.num_students()
        self.assertIsNotNone(self.sec_a.num_students(cache_only=True))
        self.assertIsNotNone(self.sec_b.num_students(cache_only=True))

        self.sec_a.preregister_student(self.students[0], overridefull=True)

        self.assertIsNone(self.sec_a.num_students(cache_only=True),
                          "the enrolled section's count should be invalidated")
        self.assertIsNotNone(self.sec_b.num_students(cache_only=True),
                             "an unrelated section's count should survive")


class WildcardScopingTest(TwoProgramCacheTest):
    """Caches whose depend_on_model wildcards were narrowed to the program that
    actually changed.  Each model reached here has a real path to a Program."""

    def test_getTimeSlotList_scoped_by_program(self):
        self.program.getTimeSlotList()
        self.program_b.getTimeSlotList()
        self.assertIsNotNone(self.program.getTimeSlotList(cache_only=True))
        self.assertIsNotNone(self.program_b.getTimeSlotList(cache_only=True))

        Event.objects.create(
            program=self.program, event_type=self.event_type,
            start=datetime(2222, 7, 12, 9, 0), end=datetime(2222, 7, 12, 10, 0),
            name='A slot', short_description='a', description='slot in A')

        self.assertIsNone(self.program.getTimeSlotList(cache_only=True))
        self.assertIsNotNone(self.program_b.getTimeSlotList(cache_only=True),
                             "program B's timeslot list should survive")

    def test_getTimeSlotList_global_event_still_dumps_everything(self):
        """Event.program is nullable; a global event must invalidate broadly."""
        self.program.getTimeSlotList()
        self.program_b.getTimeSlotList()

        Event.objects.create(
            program=None, event_type=self.event_type,
            start=datetime(2222, 7, 13, 9, 0), end=datetime(2222, 7, 13, 10, 0),
            name='global', short_description='g', description='global event')

        self.assertIsNone(self.program.getTimeSlotList(cache_only=True))
        self.assertIsNone(self.program_b.getTimeSlotList(cache_only=True))

    def test_getResourceTypes_scoped_by_program(self):
        from esp.resources.models import ResourceType
        self.program.getResourceTypes()
        self.program_b.getResourceTypes()
        self.assertIsNotNone(self.program.getResourceTypes(cache_only=True))
        self.assertIsNotNone(self.program_b.getResourceTypes(cache_only=True))

        ResourceType.objects.create(name='Projector A', program=self.program)

        self.assertIsNone(self.program.getResourceTypes(cache_only=True))
        self.assertIsNotNone(self.program_b.getResourceTypes(cache_only=True),
                             "program B's resource types should survive")

    def test_classes_timeslot_scoped_by_program(self):
        from esp.program.modules.handlers.jsondatamodule import JSONDataModule
        cf = JSONDataModule.classes_timeslot.cached_function
        #   `extra` is a timeslot id, so each program is keyed on its own slot.
        ts_a = str(self.timeslots[0].id)
        ts_b = str(self.program_b.getTimeSlots()[0].id)
        cf(ts_a, self.program); cf(ts_b, self.program_b)
        self.assertIsNotNone(cf(ts_a, self.program, cache_only=True))
        self.assertIsNotNone(cf(ts_b, self.program_b, cache_only=True))

        Event.objects.create(
            program=self.program, event_type=self.event_type,
            start=datetime(2222, 7, 14, 9, 0), end=datetime(2222, 7, 14, 10, 0),
            name='A slot 2', short_description='a2', description='another slot in A')

        self.assertIsNone(cf(ts_a, self.program, cache_only=True))
        self.assertIsNotNone(cf(ts_b, self.program_b, cache_only=True),
                             "program B's classes_timeslot should survive")
