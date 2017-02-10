"""
Utilities for use in resource constraints and scoring.
"""

import re


class ResourceCriterion:
    """A criterion for resource constraints. Has a section matcher and a
    classroom matcher. Either checks that if the section matches then the
    classroom does as well, or vice versa."""
    def __init__(self, section_matcher, classroom_matcher,
                 condition_on_section=True):
        """Construct a ResourceCriterion with the given section matcher and
        classroom matcher. condition_on_section means we check that the section
        matching implies the classroom also matches. So if condition_on_section
        is True, then our checker will return False (i.e. non-match) if the
        section matcher matches, but the classroom matcher doesn't."""
        self.section_matcher = section_matcher
        self.classroom_matcher = classroom_matcher
        self.condition_on_section = condition_on_section

    @staticmethod
    def create_from_specification(spec):
        """Construct a ResourceCriterion based on a specification string.

        The syntax is as follows, where all caps denotes a variable and
        brackets denote an optional argument:
            if PREMISE then CONCLUSION

        where PREMISE and CONCLUSION can be of the form
            section [not] requests RESTYPE [with VALUE_REGEX]
        or
            classroom [not] has RESTYPE [with VALUE_REGEX]
        or
            classroom [not] matches NAME_REGEX
        or
            any section

        and where PREMISE and CONCLUSION must not both be section criteria or
        both be classroom criteria.
        """
        criterion = re.match(r"if (.+) then (.+)", spec)
        if not criterion:
            raise ValueError(
                "ResourceCriteron spec must match 'if PREMISE then CONCLUSION")
        matchers = []
        for group in criterion.group(1, 2):
            resource_request_match = re.match(
                r"section (not)? requests (.+) (with (.+))?", group)
            if resource_request_match:
                negate, res_type, value_regex = \
                    resource_request_match.group(1, 2, 4)
                if value_regex:
                    matcher = ResourceRequestMatcher(res_type, value_regex)
                else:
                    matcher = ResourceRequestMatcher(res_type)
                if negate:
                    matcher = NegatingSectionMatcher(matcher)
                matchers.append(matcher)
                continue
            resource_classroom_match = re.match(
                r"classroom (not)? has (.+) (with (.+))?", group)
            if resource_classroom_match:
                negate, res_type, value_regex = \
                    resource_classroom_match.group(1, 2, 4)
                if value_regex:
                    matcher = ResourceClassroomMatcher(res_type, value_regex)
                else:
                    matcher = ResourceClassroomMatcher(res_type)
                if negate:
                    matcher = NegatingClassroomMatcher(matcher)
                matchers.append(matcher)
                continue
            classroom_name_match = re.match(
                r"classroom (not)? matches (.+)", group)
            if classroom_name_match:
                negate, name_regex = classroom_name_match.groups()
                matcher = ClassroomNameMatcher(name_regex)
                if negate:
                    matcher = NegatingClassroomMatcher(matcher)
                matchers.append(matcher)
                continue
            if group == "any section":
                matchers.append(TrivialSectionMatcher())
                continue
            raise ValueError(
                "Clause '{}' doesn't match a valid pattern.".format(group))
        if isinstance(matchers[0], BaseSectionMatcher):
            condition_on_section = True
            section_matcher, classroom_matcher = matchers
            if isinstance(classroom_matcher, BaseSectionMatcher):
                raise ValueError("Cannot specify two section matchers")
        else:
            condition_on_section = False
            classroom_matcher, section_matcher = matchers
            if isinstance(section_matcher, BaseClassroomMatcher):
                raise ValueError("Cannot specify two classroom matchers")
        return ResourceCriterion(section_matcher, classroom_matcher,
                                 condition_on_section)

    def check_match(self, section, room):
        """Returns False if the premise holds but the conclusion fails, True
        otherwise."""
        if self.condition_on_section:
            return (self.classroom_matcher.room_matches(room)
                    or (not self.section_matcher.section_matches(section)))
        else:
            return (not self.classroom_matcher.room_matches(room)
                    or (self.section_matcher.section_matches(section)))


class BaseSectionMatcher:
    """A base class for section matches, which Determine whether a section
    matches a given criterion."""
    def section_matches(self, section):
        raise NotImplementedError


class TrivialSectionMatcher(BaseSectionMatcher):
    """Matches all sections."""
    def section_matches(self, section):
        return True


class NegatingSectionMatcher(BaseSectionMatcher):
    """Negates another SectionMatcher."""
    def __init__(self, section_matcher):
        self.section_matcher = section_matcher

    def section_matches(self, section):
        return not(self.section_matcher.section_matches(section))


class ResourceRequestMatcher(BaseSectionMatcher):
    """Determines whether a section has a ResourceRequest matching a particular
    resource type, optionally with a regex matching the desired value."""
    def __init__(self, res_type, desired_value_regex=".*"):
        self.res_type = res_type
        self.desired_value_regex = desired_value_regex

    def section_matches(self, section):
        """Returns True if the section has this resource request,
        else False."""
        if self.res_type.name not in section.resource_requests:
            return False
        return (re.match(
            self.desired_value_regex,
            section.resource_requests[self.res_type.name].value)
            is not None)


class BaseClassroomMatcher:
    """A base class for classroom matchers, which determine whether rooms match
    a particular criterion."""
    def room_matches(self, room):
        raise NotImplementedError


class NegatingClassroomMatcher:
    """Negates another ClassroomMatcher."""
    def __init__(self, room_matcher):
        self.room_matcher = room_matcher

    def section_matches(self, room):
        return not(self.room_matcher.room_matches(room))


class ResourceClassroomMatcher(BaseClassroomMatcher):
    """Determines whether a classroom has a Resource matching a particular
    resource type, optionally with a regex matching the attribute value."""
    def __init__(self, res_type, attribute_value_regex=".*"):
        self.res_type = res_type
        self.attribute_value_regex = attribute_value_regex

    def room_matches(self, room):
        """Returns True if the room has this resource request, else False."""
        if self.res_type.name not in room.furnishings:
            return False
        return (re.match(
            self.attribute_value_regex,
            room.furnishings[self.res_type.name].value)
            is not None)


class ClassroomNameMatcher(BaseClassroomMatcher):
    """Determines whether a classroom's name matches a given regex."""
    def __init__(self, name_regex):
        self.name_regex = name_regex

    def room_matches(self, room):
        """Returns True if the room name matches the regex, else False."""
        return (re.match(self.name_regex, room.name) is not None)
