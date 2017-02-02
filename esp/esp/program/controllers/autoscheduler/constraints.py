# TODO: documentation on adding constraints
from esp.program.controllers.autoscheduler.models import AS_Timeslot


class BaseConstraint:
    """Abstract class for constraints."""
    default_on = True

    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        raise NotImplementedError

    # These local checks are for performance reasons. These also check
    # hypothetical operations, whereas check_schedule checks an existing
    # schedule.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        raise NotImplementedError

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        raise NotImplementedError

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns False
        if unscheduling the specified section will violate the constraint,
        True otherwise."""
        raise NotImplementedError

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns False
        if swapping two sections will violate the constraint,
        True otherwise."""
        raise NotImplementedError


class CompositeConstraint(BaseConstraint):
    """A constraint which checks all the constraints you actually want."""
    def __init__(self, constraint_names):
        """Takes in a list of constraint names, as strings."""
        self.constraints = []
        available_constraints = globals()
        for constraint in constraint_names:
            self.constraints.append(available_constraints[constraint]())

    def check_schedule(self, schedule):
        return all(map(lambda c: c.check_schedule(schedule), self.constraints))

    def check_schedule_section(self, section, start_roomslot, schedule):
        return all(map(
            lambda c: c.check_schedule_section(
                section, start_roomslot, schedule),
            self.constraints))

    def check_move_section(self, section, start_roomslot, schedule):
        return all(map(
            lambda c: c.check_move_section(
                section, start_roomslot, schedule),
            self.constraints))

    def check_unschedule_section(self, section, schedule):
        return all(map(lambda c: c.check_unschedule_section(section, schedule),
                       self.constraints))

    def check_swap_sections(self, section1, section2, schedule):
        return all(map(
            lambda c: c.check_swap_sections(section1, section2, schedule),
            self.constraints))


class ContiguousConstraint(BaseConstraint):
    """Multi-hour sections may only be scheduled across
    contiguous timeblocks in the same room."""
    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        for section in schedule.class_sections:
            if len(section.assigned_roomslots) > 1:
                section_room = section.assigned_roomslots[0].room
                prev_timeslot = \
                    section.assigned_roomslots[0].timeslot
                for roomslot in section.assigned_roomslots[1:]:
                    if not AS_Timeslot.contiguous(
                            prev_timeslot, roomslot.timeslot):
                        return False
                    if roomslot.room.id != section_room.id:
                        return False
                    prev_timeslot = roomslot.timeslot
        return True

    # These local checks are for performance reasons.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        return self.check_schedule(schedule)

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        return self.check_schedule_section(
                self, section, start_roomslot, schedule)

    def check_unschedule_section(self, section, schedule):
        """Always True"""
        return True

    def check_swap_sections(self, section1, section2, schedule):
        """Always True"""
        return True


class LunchConstraint(BaseConstraint):
    """Multi-hour sections can't be scheduled over both blocks of lunch."""
    pass  # TODO


class ResourceConstraint(BaseConstraint):
    """If a section demands an unprovided required resource."""
    pass  # TODO


class RestrictedRoomConstraint(BaseConstraint):
    """If a room demands only sections of a particular type
    (e.g. if only computer classes may be scheduled in computer labs)"""
    pass  # TODO


class RoomAvailabilityConstraint(BaseConstraint):
    """Sections can only be in rooms which are available."""
    pass  # TODO


class RoomConcurrencyConstraint(BaseConstraint):
    """Rooms can't be double-booked."""
    pass  # TODO


class SectionLengthConstraint(BaseConstraint):
    """Sections must be scheduled for exactly their length.
    This also accounts for not scheduling a section twice,
    in conjunction with consistency constraints."""
    pass  # TODO


class TeacherAvailabilityConstraint(BaseConstraint):
    """Teachers can only teach during times they are available."""
    pass  # TODO


class TeacherConcurrencyConstraint(BaseConstraint):
    """Teachers can't teach two classes at once."""
    pass  # TODO
