# TODO: documentation on adding constraints
from esp.program.controllers.autoscheduler.models import AS_Timeslot
import esp.program.controllers.autoscheduler.constants as constants


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
        for section in schedule.class_sections.itervalues():
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
        classroom = start_roomslot.room
        assigned_slots = classroom.get_roomslots_by_duration(
                start_roomslot, section.duration)
        if len(assigned_slots) == 0:
            return False
        if len(assigned_slots) == 1:
            return True
        prev_timeslot = start_roomslot.timeslot
        for roomslot in assigned_slots[1:]:
            if not AS_Timeslot.contiguous(
                    prev_timeslot, roomslot.timeslot):
                return False
            prev_timeslot = roomslot.timeslot
        return True

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


class PreconditionConstraint(BaseConstraint):
    """Checks to see if any action made satisfies its preconditions.
    The schedule check is trivial"""
    def check_schedule(self, schedule):
        """Always True"""
        return True

    # These local checks are for performance reasons. These also check
    # hypothetical operations, whereas check_schedule checks an existing
    # schedule.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Ensures that the section to be scheduled is not already
        scheduled."""
        return (len(section.assigned_roomslots) == 0)

    def check_move_section(self, section, start_roomslot, schedule):
        """Ensures that the section to be section is already scheduled."""
        return (len(section.assigned_roomslots) != 0)

    def check_unschedule_section(self, section, schedule):
        """Ensures that the section is already scheduled."""
        return (len(section.assigned_roomslots) != 0)

    def check_swap_sections(self, section1, section2, schedule):
        """Ensures that both sections are already scheduled and
        they are the same duration"""
        return (len(section1.assigned_roomslots) ==
                section2.assigned_roomslots) and (
                        len(section1.assigned_roomslots) != 0)


class ResourceConstraint(BaseConstraint):
    """If a section demands an unprovided required resource."""
    pass  # TODO


class RestrictedRoomConstraint(BaseConstraint):
    """If a room demands only sections of a particular type
    (e.g. if only computer classes may be scheduled in computer labs)"""
    pass  # TODO


class RoomAvailabilityConstraint(BaseConstraint):
    """Sections can only be in rooms which are available."""
    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        # Because of the nature of the data structure (roomslots),
        # Sections can only be scheduled if the room is available
        # at the specified timeslot. Hence everything in this constraint
        # is trivially true.
        return True

    # These local checks are for performance reasons. These also check
    # hypothetical operations, whereas check_schedule checks an existing
    # schedule.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        return True

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        return True

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns False
        if unscheduling the specified section will violate the constraint,
        True otherwise."""
        return True

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns False
        if swapping two sections will violate the constraint,
        True otherwise."""
        return True


class RoomConcurrencyConstraint(BaseConstraint):
    """Rooms can't be double-booked."""
    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        return True

    # These local checks are for performance reasons. These also check
    # hypothetical operations, whereas check_schedule checks an existing
    # schedule.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        classroom = start_roomslot.room
        assigned_roomslots = classroom.get_roomslots_by_duration(
                start_roomslot, section.duration)
        if len(assigned_roomslots) == 0:
            return False
        for roomslot in assigned_roomslots:
            if roomslot.assigned_section is not None:
                return False
        return True

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        classroom = start_roomslot.room
        assigned_roomslots = classroom.get_roomslots_by_duration(
                start_roomslot, section.duration)
        if len(assigned_roomslots) == 0:
            return False
        for roomslot in assigned_roomslots:
            if not (roomslot.assigned_section in [None, section]):
                return False
        return True

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns False
        if unscheduling the specified section will violate the constraint,
        True otherwise."""
        return True

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns False
        if swapping two sections will violate the constraint,
        True otherwise."""
        return True


class SectionDurationConstraint(BaseConstraint):
    """Sections must be scheduled for exactly their length.
    This also accounts for not scheduling a section twice,
    in conjunction with consistency constraints."""
    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        for section in schedule.class_sections.itervalues():
            if len(section.assigned_roomslots != 0):
                start_time = section.assigned_roomslots[0].timeslot.start
                end_time = section.assigned_roomslots[-1].timeslot.end
                if abs((end_time - start_time).seconds/3600.0 -
                        section.duration) > constants.DELTA_TIME:
                    return False
        return True

    # These are trivially true because of the roomslots assignment process.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        return True

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        return True

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns False
        if unscheduling the specified section will violate the constraint,
        True otherwise."""
        return True

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns False
        if swapping two sections will violate the constraint,
        True otherwise."""
        return True


class TeacherAvailabilityConstraint(BaseConstraint):
    """Teachers can only teach during times they are available."""
    pass  # TODO


class TeacherConcurrencyConstraint(BaseConstraint):
    """Teachers can't teach two classes at once."""
    pass  # TODO
