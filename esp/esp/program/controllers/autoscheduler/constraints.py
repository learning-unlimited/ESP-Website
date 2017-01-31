# TODO: documentation on adding constraints


class BaseConstraint:
    """Abstract class for constraints."""

    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        raise NotImplementedError

    # These local checks are for performance reasons.
    def check_add_section(self, section, room, start_time, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section in the room at the start time would
        violate the constraint, True otherwise."""
        return self.check_schedule(schedule)

    def check_remove_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns False
        if unscheduling the specified section will violate the constraint,
        True otherwise."""
        return self.check_schedule(schedule)

    def check_swap_section(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns False
        if swapping two sections will violate the constraint,
        True otherwise."""
        return self.check_schedule(schedule)


class ConsistencyConstraint:
    """Different parts of the schedule should be consistent.
    For example, if a section thinks it is scheduled in a room,
    the room should think a section is scheduled in it."""
    pass  # TODO


class ContiguousConstraint:
    """Multi-hour sections may only be scheduled across
    contiguous timeblocks."""
    pass  # TODO


class LunchConstraint:
    """Multi-hour sections can't be scheduled over both blocks of lunch."""
    pass  # TODO


class ResourceConstraint:
    """If a section demands an unprovided required resource."""
    pass  # TODO


class RestrictedRoomConstraint:
    """If a room demands only sections of a particular type
    (e.g. if only computer classes may be scheduled in computer labs)"""
    pass  # TODO


class RoomAvailabilityConstraint:
    """Sections can only be in rooms which are available."""
    pass  # TODO


class RoomConcurrencyConstraint:
    """Rooms can't be double-booked."""
    pass  # TODO


class SectionLengthConstraint:
    """Sections must be scheduled for exactly their length.
    This also accounts for not scheduling a section twice,
    in conjunction with consistency constraints."""
    pass  # TODO


class TeacherAvailabilityConstraint:
    """Teachers can only teach during times they are available."""
    pass  # TODO


class TeacherConcurrencyConstraint:
    """Teachers can't teach two classes at once."""
    pass  # TODO
