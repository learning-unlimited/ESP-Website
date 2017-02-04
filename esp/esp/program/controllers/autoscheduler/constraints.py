# TODO: documentation on adding constraints
import inspect

import esp.program.controllers.autoscheduler.util as util
import esp.program.controllers.autoscheduler.constants as constants


class BaseConstraint:
    """Abstract class for constraints."""
    # A constraint is required when the logic either enforces or assumes it.
    required = False

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
        required_constraints = [
                name for name, constraint in available_constraints.iteritems()
                if inspect.isclass(constraint)
                and issubclass(constraint, BaseConstraint)
                and constraint.required]
        constraints_to_use = set(constraint_names + required_constraints)
        for constraint in constraints_to_use:
            print("Using constraint {}".format(constraint))
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

    required = True  # Maybe it isn't actually, but it seems like it is.

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
                    if not util.contiguous(
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
            if not util.contiguous(
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
    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        for list_lunch_slots in schedule.lunch_timeslots.itervalues():
            start_lunch = list_lunch_slots[0].start
            end_lunch = list_lunch_slots[-1].end
            for section in schedule.class_sections:
                start_section = section.assigned_roomslots[0].timeslot.start
                end_section = section.assigned_roomslots[-1].timeslot.end
                if start_section <= start_lunch \
                        and end_section >= end_lunch:
                            return False
        return True

    # These local checks are for performance reasons. These also check
    # hypothetical operations, whereas check_schedule checks an existing
    # schedule.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        for list_lunch_slots in schedule.lunch_timeslots.itervalues():
            start_lunch = list_lunch_slots[0].start
            end_lunch = list_lunch_slots[0].end
            roomslots = start_roomslot.room.get_roomslots_by_duration(
                    start_roomslot, section.duration)
            start_section = roomslots[0].timeslot.start
            end_section = roomslots[-1].timeslot.end
            if start_section <= start_lunch and \
                    end_section >= end_lunch:
                        return False
        return True

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        return self.check_schedule_section(section, start_roomslot, schedule)

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


class PreconditionConstraint(BaseConstraint):
    """Checks to see if any action made satisfies its preconditions.
    The schedule check is trivial"""

    required = True

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

    required = True  # See note about triviality below.

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

    required = True  # A double-booked room will violate consistency checks.

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

    required = True  # I think some of the other constraints assume this.

    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        for section in schedule.class_sections.itervalues():
            if len(section.assigned_roomslots) != 0:
                start_time = section.assigned_roomslots[0].timeslot.start
                end_time = section.assigned_roomslots[-1].timeslot.end
                if abs((end_time - start_time).seconds/3600.0 -
                        section.duration) > constants.DELTA_TIME:
                    return False
        return True

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        if len(roomslots) == 0:
            return False
        start_time = roomslots[0].timeslot.start
        end_time = roomslots[-1].timeslot.end
        if abs((end_time - start_time).seconds/3600.0 -
                section.duration) > constants.DELTA_TIME:
            return False
        return True

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        return self.check_schedule_section(section, start_roomslot, schedule)

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

    required = True  # I'm not sure if it actually is, but let's be safe.

    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        for teacher in schedule.teachers.itervalues():
            for section in teacher.taught_sections.itervalues():
                if len(section.assigned_roomslots) > 0:
                    for roomslot in section.assigned_roomslots:
                        start_time = roomslot.timeslot.start
                        end_time = roomslot.timeslot.end
                        if (start_time, end_time) \
                                not in teacher.availability_dict:
                                    return False
        return True

    # These local checks are for performance reasons. These also check
    # hypothetical operations, whereas check_schedule checks an existing
    # schedule.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        room = start_roomslot.room
        roomslots = room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        for teacher in section.teachers:
            for roomslot in roomslots:
                start_time = roomslot.timeslot.start
                end_time = roomslot.timeslot.end
                if (start_time, end_time) not in \
                        teacher.availability_dict:
                            return False
        return True

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        existing_timeslots = set()
        for roomslot in section.assigned_roomslots:
            existing_timeslots.add((roomslot.timeslot.start,
                                    roomslot.timeslot.end))
        for teacher in section.teachers:
            for roomslot in roomslots:
                start_time = roomslot.timeslot.start
                end_time = roomslot.timeslot.end
                if (start_time, end_time) not in teacher.availability_dict \
                        and (start_time, end_time) not in \
                        existing_timeslots:
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
        roomslots1 = section1.assigned_roomslots
        roomslots2 = section2.assigned_roomslots
        teachers1 = section1.teachers
        teachers2 = section2.teachers
        timeslots1 = set()
        timeslots2 = set()
        for roomslot in roomslots1:
            timeslots1.add((roomslot.timeslot.start, roomslot.timeslot.end))
        for roomslot in roomslots2:
            timeslots2.add((roomslot.timeslot.start, roomslot.timeslot.end))
        for teacher in teachers1:
            for roomslot in roomslots2:
                start_time = roomslot.timeslot.start
                end_time = roomslot.timeslot.end
                if (start_time, end_time) not in teacher.availability_dict \
                        and (start_time, end_time) not in timeslots1:
                            return False
        for teacher in teachers2:
            for roomslot in roomslots1:
                start_time = roomslot.timeslot.start
                end_time = roomslot.timeslot.end
                if (start_time, end_time) not in teacher.availability_dict \
                        and (start_time, end_time) not in timeslots2:
                            return False
        return True


class TeacherConcurrencyConstraint(BaseConstraint):
    """Teachers can't teach two classes at once."""

    required = True  # This would cause a consistency check to be violated.

    def get_already_teaching_set(self, teacher):
        already_teaching = set()
        for section in teacher.taught_sections.itervalues():
            for roomslot in section.assigned_roomslots:
                already_teaching.add((
                    roomslot.timeslot.start, roomslot.timeslot.end))
        return already_teaching

    def check_schedule(self, schedule):
        """Returns False if an AS_Schedule violates the constraint,
        True otherwise."""
        for teacher in schedule.teachers.itervalues():
            already_teaching = set()
            for section in teacher.taught_sections.itervalues():
                for roomslot in section.assigned_roomslots:
                    start_time = roomslot.timeslot.start
                    end_time = roomslot.timeslot.end
                    if (start_time, end_time) in already_teaching:
                        return False
                    already_teaching.add((start_time, end_time))
        return True

    # These local checks are for performance reasons. These also check
    # hypothetical operations, whereas check_schedule checks an existing
    # schedule.
    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if scheduling the section starting at the given roomslot would
        violate the constraint, True otherwise."""
        for teacher in section.teachers:
            already_teaching = self.get_already_teaching_set(teacher)
            assigned_roomslots = start_roomslot.room.get_roomslots_by_duration(
                    start_roomslot, section.duration)
            for roomslot in assigned_roomslots:
                if (roomslot.timeslot.start, roomslot.timeslot.end) \
                        in already_teaching:
                            return False
        return True

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns False
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, True otherwise."""
        for teacher in section.teachers:
            already_teaching = self.get_already_teaching_set(teacher)
            for roomslot in section.assigned_roomslots:
                start_time = roomslot.timeslot.start
                end_time = roomslot.timeslot.end
                already_teaching.remove((start_time, end_time))
            assigned_roomslots = start_roomslot.room.get_roomslots_by_duration(
                    start_roomslot, section.duration)
            for roomslot in assigned_roomslots:
                if (roomslot.timeslot.start, roomslot.timeslot.end) \
                        in already_teaching:
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
        timeslots1 = set()
        timeslots2 = set()
        for roomslot in section1.assigned_roomslots:
            timeslots1.add((roomslot.timeslot.start, roomslot.timeslot.end))
        for roomslot in section2.assigned_roomslots:
            timeslots2.add((roomslot.timeslot.start, roomslot.timeslot.end))
        for teacher in section1.teachers:
            already_teaching = self.get_already_teaching_set(teacher)
            for time in timeslots2:
                if time in already_teaching and time not in timeslots1:
                    return False
        for teacher in section2.teachers:
            already_teaching = self.get_already_teaching_set(teacher)
            for time in timeslots1:
                if time in already_teaching and time not in timeslots2:
                    return False
        return True
