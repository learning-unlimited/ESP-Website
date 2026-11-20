"""Tests for the autoscheduler's resource criteria."""

import unittest

from esp.program.controllers.autoscheduler import data_model
from esp.program.controllers.autoscheduler.resource_checker import (
    ClassroomNameMatcher, NegatingClassroomMatcher, NegatingSectionMatcher,
    ResourceClassroomMatcher, ResourceCriterion, ResourceRequestMatcher,
    TrivialSectionMatcher, create_resource_criteria)

VALID_TYPES = {"Projector", "Computer"}


def make_section(**requests):
    """A section requesting the given resources (name -> value)."""
    resources = {name: data_model.AS_ResourceType(name, i, value)
                 for i, (name, value) in enumerate(requests.items())}
    return data_model.AS_ClassSection(
        [], 1.0, 20, 0, [], 1, 0, resource_requests=resources)


def make_room(name="26-100", **furnishings):
    """A classroom with the given furnishings (name -> value)."""
    resources = {res: data_model.AS_ResourceType(res, i, value)
                 for i, (res, value) in enumerate(furnishings.items())}
    return data_model.AS_Classroom(name, 30, [], furnishings=resources)


def parse(spec):
    """Parse a criterion with the standard valid types."""
    return ResourceCriterion.create_from_specification(
        spec, "test", VALID_TYPES)


class CreateFromSpecificationTest(unittest.TestCase):
    """Parsing criterion specifications."""

    def test_section_premise(self):
        """A section premise conditions on the section."""
        criterion = parse("if section requests Projector then "
                          "classroom has Projector")
        self.assertTrue(criterion.condition_on_section)
        self.assertIsInstance(criterion.section_matcher,
                              ResourceRequestMatcher)
        self.assertIsInstance(criterion.classroom_matcher,
                              ResourceClassroomMatcher)

    def test_classroom_premise(self):
        """A classroom premise does not condition on the section."""
        criterion = parse("if classroom has Computer then any section")
        self.assertFalse(criterion.condition_on_section)
        self.assertIsInstance(criterion.section_matcher,
                              TrivialSectionMatcher)

    def test_negations(self):
        """"not" wraps section and classroom matchers."""
        criterion = parse("if not section requests Projector then "
                          "not classroom has Computer")
        self.assertIsInstance(criterion.section_matcher,
                              NegatingSectionMatcher)
        self.assertIsInstance(criterion.classroom_matcher,
                              NegatingClassroomMatcher)

    def test_value_regex_and_name_match(self):
        """"with" supplies a value regex and "classroom matches" a name."""
        criterion = parse("if section requests Projector with HD then "
                          "classroom matches 26-.*")
        self.assertEqual(criterion.section_matcher.desired_value_regex, "HD")
        self.assertIsInstance(criterion.classroom_matcher,
                              ClassroomNameMatcher)

    def test_malformed_specs_raise(self):
        """Specs that aren't "if X then Y" or have bad clauses are rejected."""
        for spec in ["nonsense", "if any section then", "if foo then bar",
                     "if any section then any section",
                     "if classroom has Computer then classroom has Projector"]:
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    parse(spec)

    def test_unknown_section_resource_type_raises(self):
        """A section clause naming an unknown resource type is rejected."""
        with self.assertRaises(ValueError):
            parse("if section requests Typo then classroom matches .*")

    def test_unknown_classroom_resource_type_raises(self):
        """A classroom clause naming an unknown resource type is rejected
        too, rather than silently never matching."""
        with self.assertRaises(ValueError):
            parse("if classroom has Typo then any section")
        with self.assertRaises(ValueError):
            parse("if any section then not classroom has Typo")

    def test_str_round_trip(self):
        """str() gives back a spec that parses to the same string."""
        for spec in [
                "if section requests Projector then classroom has Projector",
                "if not section requests Projector with HD then "
                "classroom matches 26-.*",
                "if classroom has Computer with Mac then any section",
                "if not classroom matches 10-.* then any section"]:
            with self.subTest(spec=spec):
                criterion = parse(spec)
                self.assertEqual(str(criterion), f"test: {spec}")
                reparsed = parse(str(criterion).split(": ", 1)[1])
                self.assertEqual(str(reparsed), str(criterion))


class CheckMatchTest(unittest.TestCase):
    """ResourceCriterion.check_match."""

    def test_section_condition(self):
        """If the section requests a projector the room must have one; other
        sections can go anywhere."""
        criterion = parse("if section requests Projector then "
                          "classroom has Projector")
        wants = make_section(Projector="Yes")
        plain = make_section()
        with_proj = make_room(Projector="Yes")
        without = make_room()
        self.assertTrue(criterion.check_match(wants, with_proj))
        self.assertFalse(criterion.check_match(wants, without))
        self.assertTrue(criterion.check_match(plain, with_proj))
        self.assertTrue(criterion.check_match(plain, without))

    def test_classroom_condition(self):
        """If the room has computers, only sections that request them may
        use it."""
        criterion = parse("if classroom has Computer then "
                          "section requests Computer")
        lab = make_room(Computer="Yes")
        plain_room = make_room()
        wants = make_section(Computer="Yes")
        plain = make_section()
        self.assertTrue(criterion.check_match(wants, lab))
        self.assertFalse(criterion.check_match(plain, lab))
        self.assertTrue(criterion.check_match(plain, plain_room))

    def test_value_regex(self):
        """The value regex is matched against the resource's value."""
        criterion = parse("if section requests Projector with HD then "
                          "classroom has Projector with HD")
        wants_hd = make_section(Projector="HD")
        self.assertTrue(criterion.check_match(
            wants_hd, make_room(Projector="HD")))
        self.assertFalse(criterion.check_match(
            wants_hd, make_room(Projector="VGA")))
        self.assertTrue(criterion.check_match(
            make_section(Projector="VGA"), make_room(Projector="VGA")))

    def test_classroom_name_matcher(self):
        """Name matching is a regex match from the start of the name."""
        criterion = parse("if any section then classroom matches 26-.*")
        section = make_section()
        self.assertTrue(criterion.check_match(section, make_room("26-100")))
        self.assertFalse(criterion.check_match(section, make_room("10-250")))

    def test_negated_matchers(self):
        """Negation flips the result of section and classroom matchers."""
        criterion = parse("if not section requests Projector then "
                          "not classroom has Projector")
        plain = make_section()
        self.assertTrue(criterion.check_match(plain, make_room()))
        self.assertFalse(criterion.check_match(
            plain, make_room(Projector="Yes")))
        self.assertTrue(criterion.check_match(
            make_section(Projector="Yes"), make_room(Projector="Yes")))


class CreateResourceCriteriaTest(unittest.TestCase):
    """create_resource_criteria."""

    def test_later_dicts_override_earlier_ones(self):
        """A name in a later dict replaces the same name in an earlier one."""
        criteria = create_resource_criteria(
            [{"a": "if any section then classroom matches 26-.*"},
             {"a": "if any section then classroom matches 10-.*"}],
            VALID_TYPES)
        self.assertEqual(len(criteria), 1)
        self.assertEqual(criteria[0].classroom_matcher.name_regex, "10-.*")

    def test_none_disables_criterion(self):
        """"None" (or None) removes a criterion."""
        criteria = create_resource_criteria(
            [{"a": "if any section then classroom matches 26-.*",
              "b": "if any section then classroom matches 10-.*"},
             {"a": "None", "b": None}],
            VALID_TYPES)
        self.assertEqual(criteria, [])

    def test_use_weights(self):
        """With use_weights, specs are (spec, weight) pairs and the weight
        is returned alongside each criterion."""
        criteria = create_resource_criteria(
            [{"a": ("if any section then classroom matches 26-.*", 5),
              "b": ("None", 3)}],
            VALID_TYPES, use_weights=True)
        self.assertEqual(len(criteria), 1)
        criterion, weight = criteria[0]
        self.assertEqual(criterion.name, "a")
        self.assertEqual(weight, 5)
