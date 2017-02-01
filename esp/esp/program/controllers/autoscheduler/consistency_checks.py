"""
Consistency checks for an AS_Schedule. For debugging purposes.
"""


class ConsistencyError(Exception):
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

    def check_section_and_teacher_consistency(self, schedule):
        """Make sure that teachers know what sections they're teaching and vice
        versa."""
        pass  # teachers don't have sections teaching yet

    def check_events_consistency(self, schedule):
        """Check to make sure that events, are consistent with timeslots,
        classrooms, and sections."""
        # Find all the events we can find, and make sure they're consistent
        # with their sources.
        existing_events = set()
        for room in schedule.classrooms:
            for event in room.availability:
                if event.room != room:
                    raise ConsistencyError("Room and event were inconsistent")
            existing_events.update(room.availability)
        for section in schedule.class_sections:
            for event in section.assigned_events:
                if event.assigned_section != section:
                    raise ConsistencyError(
                            "Section and event were inconsistent")
            existing_events.update(section.assigned_events)
        for timeslot in schedule.timeslots:
            for event in timeslot.associated_events:
                if event.timeslot is not timeslot:
                    raise ConsistencyError(
                            "Timeslot and event were inconsistent")
            existing_events.update(section.assigned_events)

        # Make sure all events we found are listed everywhere they should be.
        for event in existing_events:
            if event.timeslot not in schedule.timeslots:
                raise ConsistencyError("Event's timeslot wasn't registered")
            if event not in event.timeslot.associated_events:
                raise ConsistencyError(
                    "Event wasn't in timeslots's associated events")
            if event.room not in schedule.classrooms:
                raise ConsistencyError("Event's room wasn't registered")
            if event not in event.room.availability:
                raise ConsistencyError("Event wasn't in room's availability")
            if event.assigned_section is not None:
                if event.assigned_section not in schedule.class_sections:
                    raise ConsistencyError("Event had an unregistered section")
                if event not in event.assigned_section.assigned_events:
                    raise ConsistencyError(
                        "Event wasn't in section's assigned events")
