import random

from django.db import connection
from django.test.utils import CaptureQueriesContext

from esp.program.models import ClassSection
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import Resource, ResourceAssignment


class CapacityPrefetchTest(ProgramFrameworkTest):
    """ClassSection.prefetch_capacity_data() must match the per-section path.

    _get_capacity() falls back to classrooms() when nothing is preloaded, so
    these compare the two against each other rather than against fixed
    numbers.
    """

    def setUp(self):
        super().setUp(
            num_timeslots=3,
            num_rooms=6,
            num_teachers=6,
            classes_per_teacher=2,
            num_students=0,
        )
        self.schedule_randomly()

        #   A local RNG: seeding the global one would perturb the random
        #   stream that other tests in the suite draw from.
        rng = random.Random(4)
        #   Vary the room capacities so the minimum-over-timeblocks logic in
        #   _get_room_capacity() actually decides the answer for some sections,
        #   rather than class_size_max shadowing it everywhere.
        for room in Resource.objects.filter(event__program=self.program,
                                            res_type__name="Classroom"):
            room.num_students = rng.choice([5, 17, 40])
            room.save()

        self.sections = list(self.program.sections())

        #   Exercise the branches that do not go through the rooms at all.
        for sec in self.sections[:2]:
            sec.max_class_capacity = 11
            sec.save()
        for sec in self.sections[2:5]:
            parent = sec.parent_class
            parent.class_size_max = None
            parent.class_size_optimal = 23
            parent.save()

        #   A section spanning two timeblocks: capacity is the smaller room.
        rooms = list(Resource.objects.filter(event__program=self.program,
                                             res_type__name="Classroom"))
        spanning = self.sections[5]
        first = spanning.resourceassignment_set.select_related('resource').first()
        if first is not None:
            elsewhere = [r for r in rooms if r.event_id != first.resource.event_id]
            if elsewhere:
                ResourceAssignment.objects.create(
                    resource=rng.choice(elsewhere), target=spanning)

        #   A duplicate assignment of a room already attached to the section.
        #   classrooms() filters resources by id, so this must not double-count.
        duplicated = self.sections[6]
        existing = duplicated.resourceassignment_set.first()
        if existing is not None:
            ResourceAssignment.objects.create(
                resource=existing.resource, target=duplicated)

        #   A section with no rooms at all.
        self.sections[7].resourceassignment_set.all().delete()

    def _fresh(self):
        """Sections with nothing preloaded, so _get_capacity() queries."""
        return {s.id: s for s in self.program.sections()}

    def _preloaded(self):
        return {s.id: s for s in
                ClassSection.prefetch_capacity_data(self.program.sections())}

    def test_capacity_matches_unprefetched(self):
        plain, preloaded = self._fresh(), self._preloaded()
        self.assertEqual(set(plain), set(preloaded))
        self.assertTrue(plain, "no sections to compare")

        for section_id in plain:
            for ignore_changes in (False, True):
                self.assertEqual(
                    plain[section_id]._get_capacity(
                        ignore_changes=ignore_changes, use_cache=False),
                    preloaded[section_id]._get_capacity(
                        ignore_changes=ignore_changes, use_cache=False),
                    "capacity differs for section %d (ignore_changes=%s)"
                    % (section_id, ignore_changes))

    def test_room_counts_match_classrooms(self):
        plain, preloaded = self._fresh(), self._preloaded()
        for section_id, section in preloaded.items():
            self.assertEqual(
                section._num_classrooms, len(plain[section_id].classrooms()),
                "room count differs for section %d" % section_id)

    def test_capacities_are_not_all_identical(self):
        """Guard against the fixture making every branch return the same number."""
        preloaded = self._preloaded()
        capacities = {s._get_capacity(use_cache=False)
                      for s in preloaded.values()}
        self.assertGreater(
            len(capacities), 1,
            "fixture produced a single capacity (%s), so the comparison "
            "tests would pass without exercising the room logic" % capacities)

    def test_prefetch_issues_exactly_one_resource_query(self):
        """The preload itself must be one query, not one per section."""
        sections = list(self.program.sections())
        self.assertGreater(len(sections), 1, "need several sections to be meaningful")
        with CaptureQueriesContext(connection) as ctx:
            ClassSection.prefetch_capacity_data(sections)
        resource_queries = [q for q in ctx.captured_queries
                            if 'resources_' in q['sql']]
        self.assertEqual(
            len(resource_queries), 1,
            "preload should issue one resource query for %d sections, got %d"
            % (len(sections), len(resource_queries)))

    def test_preloaded_capacity_issues_no_resource_queries(self):
        sections = ClassSection.prefetch_catalog_data(self.program.sections())
        with CaptureQueriesContext(connection) as ctx:
            for section in sections:
                section._get_capacity(use_cache=False)
        resource_queries = [q for q in ctx.captured_queries
                            if 'resources_' in q['sql']]
        self.assertEqual(
            resource_queries, [],
            "preloaded sections should not query resources; got %d queries"
            % len(resource_queries))
