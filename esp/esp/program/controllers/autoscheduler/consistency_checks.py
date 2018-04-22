""" Checks for schedule integrity.

A consistency check verifies whether an AS_Schedule satisfies various
invariants in the models/data structures, and which we assume the code enforces
implicitly; for example, if a certain fact is stored in two different ways in
an AS_Schedule, then we expect these two different ways to always agree with
each other. Conversely, it is expected to be impossible for a schedule to fail
a consistency check unless there are bugs in the code.
"""
import logging

from esp.program.controllers.autoscheduler import util

logger = logging.getLogger(__name__)


class ConsistencyError(Exception):
    """An error caught by a consistency check."""
    pass


class ConsistencyChecker:
    """A class for running consistency checks on an AS_Schedule.

    Consistency checks should be of the form "check_(something)_consistency".
    """

    def run_all_consistency_checks(self, schedule):
        """Runs all consistency checks in this module, i.e. all functions
        which are named check_[something]_consistency."""
        for attr in dir(self):
            if attr.startswith("check_") and attr.endswith("_consistency"):
                logger.info("Running: {}".format(attr))
                getattr(self, attr)(schedule)

    def check_availability_dict_consistency(self, schedule):
        """Ensure that room and teacher availability dicts agree with their
        availability lists and that keys agree with values"""
        for room in schedule.classrooms.itervalues():
            for time, roomslot in room.availability_dict.iteritems():
                if time != (roomslot.timeslot.start, roomslot.timeslot.end):
                    raise ConsistencyError(
                        ("Room availability dict key/value mismatch for "
                         "room {}").format(room.name))
            if set(room.availability) != set(
                    room.availability_dict.itervalues()):
                raise ConsistencyError(
                    "Room {} availability list and dict don't match"
                    .format(room.name))
        for teacher in schedule.teachers.itervalues():
            for time, timeslot in teacher.availability_dict.iteritems():
                if time != (timeslot.start, timeslot.end):
                    raise ConsistencyError(
                        ("Teacher availability dict key/value mismatch for "
                         "teacher {}").format(teacher.id))
            if set(t.id for t in teacher.availability) != set(
                    t.id for t in teacher.availability_dict.itervalues()):
                raise ConsistencyError(
                    "Teacher {} availability list and dict don't match"
                    .format(teacher.id))

    def check_lunch_consistency(self, schedule):
        """Checks that lunch dictionary maps correctly,
        and slots are sorted, and all timeslots are registered"""
        for day in schedule.lunch_timeslots:
            for timeslot1, timeslot2 in zip(
                    schedule.lunch_timeslots[day],
                    schedule.lunch_timeslots[day][1:]):
                if timeslot1 == timeslot2:
                    raise ConsistencyError(
                        "Duplicate lunch timeslots detected.")
                if timeslot1 > timeslot2:
                    raise ConsistencyError("Lunch timeslots weren't sorted.")
                if timeslot1.end > timeslot2.start:
                    raise ConsistencyError("Lunch timeslots are overlapping.")
            for timeslot in schedule.lunch_timeslots[day]:
                if (timeslot.start.year, timeslot.start.month,
                        timeslot.start.day) != day:
                    raise ConsistencyError("Incorrect mapping of slots\
                            in lunch.")
                # Check to make sure the timeslot is registered.
                # First make sure that a timeslot in the schedule's list of
                # timeslots matches the lunch timeslot, then check to make sure
                # that it's actually exactly the same timeslot (as opposed to
                # just an equal one), which wouldn't have the same associated
                # roomslots.
                if timeslot not in schedule.timeslots \
                        or timeslot is not schedule.timeslots[
                            schedule.timeslots.index(timeslot)]:
                    raise ConsistencyError("Lunch timeslot isn't registered")

    def check_resource_dict_consistency(self, schedule):
        """Ensure that sections' resource request dicts and rooms' furnishings
        dicts have key/value consistency."""
        for section in schedule.class_sections.itervalues():
            for restype_name, request in section.resource_requests.iteritems():
                if request.name != restype_name:
                    raise ConsistencyError(
                        "Section {} had request {} listed under name {}"
                        .format(section.id, request.name, restype_name))
        for room in schedule.classrooms.itervalues():
            for restype_name, furnishing in room.furnishings.iteritems():
                if furnishing.name != restype_name:
                    raise ConsistencyError(
                        "Room {} had furnishing {} listed under name {}"
                        .format(room.name, furnishing.name, restype_name))

    def check_roomslots_consistency(self, schedule):
        """Check to make sure that roomslots, are consistent with timeslots,
        classrooms, and sections."""
        # Find all the roomslots we can find, and make sure they're consistent
        # with their sources.
        existing_roomslots = set()
        for room in schedule.classrooms.itervalues():
            for roomslot in room.availability:
                if roomslot.room != room:
                    raise ConsistencyError(
                            "Room and roomslot were inconsistent")
            existing_roomslots.update(room.availability)
        for section in schedule.class_sections.itervalues():
            for roomslot in section.assigned_roomslots:
                if roomslot.assigned_section != section:
                    raise ConsistencyError(
                            "Section and roomslot were inconsistent")
            existing_roomslots.update(section.assigned_roomslots)
        for timeslot in schedule.timeslots:
            for roomslot in timeslot.associated_roomslots:
                if roomslot.timeslot is not timeslot:
                    raise ConsistencyError(
                            "Timeslot and roomslot were inconsistent")
            existing_roomslots.update(timeslot.associated_roomslots)

        # Make sure all roomslots we found are listed everywhere they should
        # be.
        for roomslot in existing_roomslots:
            # We need to check that the roomslot's timeslot is actually the
            # timeslot which is registered, as opposed to just an "equivalent"
            # one, because two equivalent timeslots might not have the same set
            # of associated roomslots.
            if roomslot.timeslot not in schedule.timeslots \
                    or roomslot.timeslot is not schedule.timeslots[
                        schedule.timeslots.index(roomslot.timeslot)]:
                raise ConsistencyError("Event's timeslot wasn't registered")
            if roomslot not in roomslot.timeslot.associated_roomslots:
                raise ConsistencyError(
                    "Event wasn't in timeslots's associated roomslots")
            if roomslot.room.name not in schedule.classrooms:
                raise ConsistencyError("Event's room wasn't registered")
            if roomslot not in roomslot.room.availability:
                raise ConsistencyError("Event wasn't in room's availability")
            if roomslot.assigned_section is not None:
                if roomslot.assigned_section.id not in \
                        schedule.class_sections:
                    raise ConsistencyError("Event had an unregistered section")
                if roomslot not in \
                        roomslot.assigned_section.assigned_roomslots:
                    raise ConsistencyError(
                        "Event wasn't in section's assigned roomslots")

    def check_roomslot_next_and_index_consistency(self, schedule):
        """Checks that all roomslots' next and index values are set
        correctly."""
        for room in schedule.classrooms.itervalues():
            for i, roomslot in enumerate(room.availability):
                if i != roomslot.index():
                    raise ConsistencyError((
                            "Roomslot index for room {} was {} instead of {}."
                    ).format(room.name, roomslot.index(), i))
                if i < len(room.availability) - 1:
                    if room.availability[i + 1] != roomslot.next():
                        raise ConsistencyError(
                            "Roomslot next for room {} was wrong.".format(
                                room.name))
                else:
                    if roomslot.next() is not None:
                        raise ConsistencyError((
                                "Last roomslot next for room {} was not None."
                        ).format(room.name))

    def roomslot_sorting_helper(self, roomslots):
        """Returns True if the roomslots are sorted by timeslot, False
        otherwise. There should not be duplicated timeslots."""
        return all(rs1.timeslot < rs2.timeslot for rs1, rs2 in
                   zip(roomslots, roomslots[1:]))

    def check_schedule_dicts_consistency(self, schedule):
        """Check the schedule's sections, teachers, and classroom dicts for
        key/value consistency."""
        for section_id, section in schedule.class_sections.iteritems():
            if section.id != section_id:
                raise ConsistencyError(
                    "Section {} was listed under id {}".format(
                        section.id, section_id))
        for teacher_id, teacher in schedule.teachers.iteritems():
            if teacher.id != teacher_id:
                raise ConsistencyError(
                    "Teacher {} was listed under id {}".format(
                        teacher.id, teacher_id))
        for room_name, room in schedule.classrooms.iteritems():
            if room.name != room_name:
                raise ConsistencyError(
                    "Room {} was listed under name {}".format(
                        room.name, room_name))

    def check_sorting_consistency(self, schedule):
        """Checks whether section assigned roomslots, classroom availability,
        and teacher availability are sorted."""
        for section in schedule.class_sections.itervalues():
            if not self.roomslot_sorting_helper(section.assigned_roomslots):
                raise ConsistencyError(
                    "Section assigned roomslots weren't sorted.")
        for classroom in schedule.classrooms.itervalues():
            if not self.roomslot_sorting_helper(classroom.availability):
                raise ConsistencyError(
                    "Classroom availability wasn't sorted.")
        for teacher in schedule.teachers.itervalues():
            if not all(t1 < t2 for t1, t2 in
                       zip(teacher.availability, teacher.availability[1:])):
                raise ConsistencyError(
                    "Teacher availability wasn't sorted.")

    def check_teacher_taught_sections_consistency(self, schedule):
        """Make sure that the taught_sections dict has keys matching values,
        and that all sections are listed by their teachers, and vice versa."""
        for teacher in schedule.teachers.itervalues():
            for section_id, section in teacher.taught_sections.iteritems():
                if section_id != section.id:
                    raise ConsistencyError(
                        "Teacher {} taught_sections had key/value mismatch"
                        .format(teacher.id))
                if teacher not in section.teachers:
                    raise ConsistencyError(
                        ("Teacher {} taught_sections listed a section the "
                         "teacher wasn't teaching").format(teacher.id))
        for section in schedule.class_sections.itervalues():
            for teacher in section.teachers:
                if section.id not in teacher.taught_sections:
                    raise ConsistencyError(
                        "Teacher{} is teaching section {} but didn't know it"
                        .format(teacher.id, section.id))

    def check_timeslot_consistency(self, schedule):
        """Checks that timeslots are sorted and non-overlapping."""
        for timeslot1, timeslot2 in zip(
                schedule.timeslots, schedule.timeslots[1:]):
            if timeslot1 == timeslot2:
                raise ConsistencyError("Duplicate timeslots detected.")
            if timeslot1 > timeslot2:
                raise ConsistencyError("Timeslots weren't sorted.")
            if timeslot1.end > timeslot2.start:
                # Strictly speaking this is the only test we need.
                # But we can keep the other two for debugging clarity.
                raise ConsistencyError("Timeslots are overlapping.")

    def check_timeslot_duration_consistency(self, schedule):
        """Ensure that timeslots' durations match their actual durations."""
        for timeslot in schedule.timeslots:
            actual_duration = util.hours_difference(
                    timeslot.start, timeslot.end)
            if abs(timeslot.duration - actual_duration) > 1e-4:
                raise ConsistencyError(
                    "Timeslot actual duration {} didn't match advertised {}"
                    .format(actual_duration, timeslot.duration))

    def check_timeslot_span_consistency(self, schedule):
        """Ensure timeslots don't span multiple days."""
        for timeslot in schedule.timeslots:
            start = timeslot.start
            end = timeslot.end
            if (start.year, start.month, start.day) != \
                    (end.year, end.month, end.day):
                raise ConsistencyError(
                    "Timeslot ({}, {}) spans multiple days".format(
                        start, end))

    def check_timeslots_list_and_dict_consistency(self, schedule):
        """Check that the timeslot dict has consistent keys and values,
        and that the list and dict have the same entries."""
        visited = {times: False for times in schedule.timeslot_dict}
        for timeslot in schedule.timeslots:
            if (timeslot.start, timeslot.end) not in schedule.timeslot_dict:
                raise ConsistencyError(
                        "Timeslot in list was missing from dict")
            visited[(timeslot.start, timeslot.end)] = True
        for times in schedule.timeslot_dict:
            if not visited[times]:
                raise ConsistencyError(
                        "Timeslot in dict was missing from list")
            timeslot = schedule.timeslot_dict[times]
            if (timeslot.start, timeslot.end) != times:
                raise ConsistencyError(
                        "Timeslot didn't match key in dict")
