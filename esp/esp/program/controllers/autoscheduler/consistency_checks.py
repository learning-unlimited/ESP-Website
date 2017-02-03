from esp.program.controllers.autoscheduler.exceptions import ConsistencyError

"""
Consistency checks for an AS_Schedule. For debugging purposes.
"""


class ConsistencyChecker:
    """A class for running consistency checks on an AS_Schedule.

    Consistency checks should be of the form "check_(something)_consistency".
    """

    def run_all_consistency_checks(self, schedule):
        """Runs all consistency checks in this module, i.e. all functions
        which are named check_[something]_consistency."""
        for attr in dir(self):
            if attr.startswith("check_") and attr.endswith("_consistency"):
                print "Running: {}".format(attr)
                getattr(self, attr)(schedule)

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

    def roomslot_sorting_helper(self, roomslots):
        """Returns True if the roomslots are sorted by timeslot, False
        otherwise. There should not be duplicated timeslots."""
        return all(rs1.timeslot < rs2.timeslot for rs1, rs2 in
                   zip(roomslots, roomslots[1:]))

    def check_section_and_teacher_consistency(self, schedule):
        """Make sure that teachers know what sections they're teaching and vice
        versa."""
        pass  # teachers don't have sections teaching yet

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
            if roomslot.timeslot not in schedule.timeslots:
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
