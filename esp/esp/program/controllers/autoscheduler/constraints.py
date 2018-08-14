"""Checkers to disallow invalid schedules and schedule manipulations.

TO ADD NEW CONSTRAINTS:
Create a class to extend the BaseConstraint class, and update config.py to list
a description. If your constraint is required, set the
appropriate attribute to override the value set in BaseConstraint; otherwise,
set a default for it in config.py.

A Constraint checks whether a schedule is "legal", e.g. teachers teaching
when they aren't available is illegal. Constraints are used to determine which
schedule manipulations are possible at any given point.

Constraints differ from ConsistencyChecks in that (typically) we expect it is
possible for data structures to store a self-consistent representation which
violates a constraint but not a consistency check.

Note, however, that the code may assume or enforce that some constraint is met;
since constraints are what the code uses to determine which schedule
manipulations are possible, we mark those constraints as required to avoid
violating these assumptions, or avoid giving the impression that the code is
not following the constraint.

Constraints are generally expected to be local, i.e. to only depend on a few
things, e.g. teachers-can't-teach-two-classes-at-once only depends on the
teacher's taught classes. Consequently, we don't allow Constraints to store
state for simplicity. (Many of these constraints also cannot reasonably depend
exclusively on state, because although constraints are local, their
dependencies often cannot be summarized in a structure much simpler than an
AS_Schedule itself. Having an internal state and also passing in a schedule
seems too fragile.)
"""

import inspect
import logging

import esp.program.controllers.autoscheduler.util as util
import esp.program.controllers.autoscheduler.config as config

logger = logging.getLogger(__name__)


class ConstraintViolation(object):
    """A constraint violation. Contains help text."""
    def __init__(self, constraint_name, reason):
        self.constraint_name = constraint_name
        self.reason = reason

    def __str__(self):
        return "Constraint {} was violated because {}".format(
            self.constraint_name, self.reason)


class BaseConstraint(object):
    """Abstract class for constraints. A Constraint can check whether a schedule
    satisfies a constraint, as well as whether a schedule would continue to
    satisfy a constraint after a hypothetical schedule manipulation."""
    # A constraint is required when the logic either enforces or assumes it.
    required = False

    def __init__(self, **kwargs):
        # Create a constructor wihch takes in arbitrary kwargs in case any
        # subclass needs them.
        pass

    def check_schedule(self, schedule):
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""
        raise NotImplementedError

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a
        ConstraintViolation if scheduling the section starting at the given
        roomslot would violate the constraint, None otherwise."""
        raise NotImplementedError

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
        raise NotImplementedError

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if unscheduling the specified section will violate the constraint,
        None otherwise."""
        raise NotImplementedError

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if swapping two sections will violate the constraint,
        None otherwise."""
        raise NotImplementedError


class CompositeConstraint(BaseConstraint):
    """A constraint which checks all the constraints you actually want."""
    def __init__(self, constraint_names, **kwargs):
        """Takes in a list of constraint names, as strings. Loads those
        constraints, as well as all the required constraints. You can also use
        'all' for the list of constraint names."""
        self.constraints = []
        available_constraints = get_all_constraint_classes_dict()
        required_constraints = get_required_constraint_names()
        if constraint_names == "all":
            constraints_to_use = available_constraints
        else:
            constraints_to_use = set(constraint_names + required_constraints)
        for constraint in constraints_to_use:
            logger.info("Using constraint {}".format(constraint))
            self.constraints.append(
                available_constraints[constraint](**kwargs))

    @util.timed_func("CompositeConstraint_check_schedule")
    def check_schedule(self, schedule):
        for c in self.constraints:
            violation = c.check_schedule(schedule)
            if violation:
                return violation
        return None

    @util.timed_func("CompositeConstraint_check_schedule_section")
    def check_schedule_section(self, section, start_roomslot, schedule):
        for c in self.constraints:
            violation = c.check_schedule_section(
                section, start_roomslot, schedule)
            if violation:
                return violation
        return None

    @util.timed_func("CompositeConstraint_check_move_section")
    def check_move_section(self, section, start_roomslot, schedule):
        for c in self.constraints:
            violation = c.check_move_section(section, start_roomslot, schedule)
            if violation:
                return violation
        return None

    @util.timed_func("CompositeConstraint_check_unschedule_section")
    def check_unschedule_section(self, section, schedule):
        for c in self.constraints:
            violation = c.check_unschedule_section(section, schedule)
            if violation:
                return violation
        return None

    @util.timed_func("CompositeConstraint_check_swap_sections")
    def check_swap_sections(self, section1, section2, schedule):
        for c in self.constraints:
            violation = c.check_swap_section(section1, section2, schedule)
            if violation:
                return violation
        return None


class ContiguousConstraint(BaseConstraint):
    """Multi-hour sections may only be scheduled across
    contiguous timeblocks in the same room."""

    required = True  # Maybe it isn't actually, but it seems like it is.

    def check_schedule(self, schedule):
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""
        for section in schedule.class_sections.itervalues():
            if len(section.assigned_roomslots) > 1:
                section_room = section.assigned_roomslots[0].room
                prev_timeslot = \
                    section.assigned_roomslots[0].timeslot
                for roomslot in section.assigned_roomslots[1:]:
                    if not util.contiguous(
                            prev_timeslot, roomslot.timeslot):
                        return ConstraintViolation(
                            self.__class__.__name__,
                            "Section id {} had noncontiguous rooms"
                            .format(section.id))
                    if roomslot.room.name != section_room.name:
                        return ConstraintViolation(
                            self.__class__.__name__,
                            "Section id {} is in 2 different rooms"
                            .format(section.id))
                    prev_timeslot = roomslot.timeslot
        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if scheduling the section starting at the given roomslot would
        violate the constraint, None otherwise."""
        classroom = start_roomslot.room
        assigned_slots = classroom.get_roomslots_by_duration(
                start_roomslot, section.duration)
        if len(assigned_slots) == 0:
            return ConstraintViolation(
                self.__class__.__name__,
                "Section won't be assigned any roomslots")
        if len(assigned_slots) == 1:
            return None
        prev_timeslot = start_roomslot.timeslot
        for roomslot in assigned_slots[1:]:
            if not util.contiguous(
                    prev_timeslot, roomslot.timeslot):
                return ConstraintViolation(
                    self.__class__.__name__,
                    "Insufficiently many contiguous timeslots to schedule")
            prev_timeslot = roomslot.timeslot
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
        return self.check_schedule_section(
                section, start_roomslot, schedule)

    def check_unschedule_section(self, section, schedule):
        """Always None"""
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Always None"""
        return None


class LunchConstraint(BaseConstraint):
    """Multi-hour sections can't be scheduled over both blocks of lunch."""
    def check_schedule(self, schedule):
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""
        for list_lunch_slots in schedule.lunch_timeslots.itervalues():
            start_lunch = list_lunch_slots[0].start
            end_lunch = list_lunch_slots[-1].end
            for section in schedule.class_sections:
                start_section = section.assigned_roomslots[0].timeslot.start
                end_section = section.assigned_roomslots[-1].timeslot.end
                if start_section <= start_lunch \
                        and end_section >= end_lunch:
                            return ConstraintViolation(
                                self.__class__.__name__,
                                "Section id {} is scheduled over lunch"
                                .format(section.id))
        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if scheduling the section starting at the given roomslot would
        violate the constraint, None otherwise."""
        for list_lunch_slots in schedule.lunch_timeslots.itervalues():
            start_lunch = list_lunch_slots[0].start
            end_lunch = list_lunch_slots[-1].end
            roomslots = start_roomslot.room.get_roomslots_by_duration(
                    start_roomslot, section.duration)
            start_section = roomslots[0].timeslot.start
            end_section = roomslots[-1].timeslot.end
            if start_section <= start_lunch and \
                    end_section >= end_lunch:
                        return ConstraintViolation(
                            self.__class__.__name__,
                            "Section would be scheduled over lunch")
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
        return self.check_schedule_section(section, start_roomslot, schedule)

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if unscheduling the specified section will violate the constraint,
        None otherwise."""
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if swapping two sections will violate the constraint,
        None otherwise."""
        return None


class PreconditionConstraint(BaseConstraint):
    """Checks to see if any action made satisfies its preconditions.
    The schedule check is trivial"""

    required = True

    def check_schedule(self, schedule):
        """Always None"""
        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Ensures that the section to be scheduled is not already
        scheduled."""
        if section.assigned_roomslots:
            return ConstraintViolation(
                self.__class__.__name__,
                "Section is already scheduled.")
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Ensures that the section to be section is already scheduled."""
        if not section.assigned_roomslots:
            return ConstraintViolation(
                self.__class__.__name__,
                "Section isn't scheduled")
        return None

    def check_unschedule_section(self, section, schedule):
        """Ensures that the section is already scheduled."""
        if not section.assigned_roomslots:
            return ConstraintViolation(
                self.__class__.__name__,
                "Section isn't scheduled")
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Ensures that both sections are already scheduled and
        they are the same duration"""
        if (len(section1.assigned_roomslots) !=
                len(section2.assigned_roomslots)):
            return ConstraintViolation(
                self.__class__.__name__,
                "Sections aren't assigned to the same number of roomslots")
        if not section1.assigned_roomslots:
            return ConstraintViolation(
                self.__class__.__name__,
                "Sections aren't scheduled")
        return None


class ResourceCriteriaConstraint(BaseConstraint):
    """Check to make sure all resource criteria (a list passed to the
    constructor with the keyword arg resource_criteria) are satisfied. This
    does NOT check whether existing sections satisfy these resource criteria,
    so that we can specify resource-based constraints to the autoscheduler but
    humans can make exceptions manually."""
    def __init__(self, **kwargs):
        super(ResourceCriteriaConstraint, self).__init__(**kwargs)
        self.resource_criteria = kwargs.get("resource_criteria", [])

    def check_schedule(self, schedule):
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""
        # This is trivial; see above note.
        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a
        ConstraintViolation
        if scheduling the section starting at the given roomslot would
        violate the constraint, None otherwise."""
        for resource_criterion in self.resource_criteria:
            if not resource_criterion.check_match(
                    section, start_roomslot.room):
                return ConstraintViolation(
                    self.__class__.__name__,
                    "Violates resource criterion '{}'.".format(
                        resource_criterion))
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
        return self.check_schedule_section(section, start_roomslot, schedule)

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if unscheduling the specified section will violate the constraint,
        None otherwise."""
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if swapping two sections will violate the constraint,
        None otherwise."""
        return self.check_schedule_section(
                section1, section2.assigned_roomslots[0]) \
            or self.check_schedule_section(
                section2, section1.assigned_roomslots[0])


class RoomAvailabilityConstraint(BaseConstraint):
    """Sections can only be in rooms which are available."""

    # This constraint is trivial (see below) and therefore enforced, therefore
    # required.
    required = True

    def check_schedule(self, schedule):
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""

        # Because of the nature of the data structure (roomslots), Sections can
        # only be scheduled if the room is available at the specified timeslot.
        # Hence everything in this constraint is trivially true. We
        # nevertheless decide to have this trivial constraint because we don't
        # expect it to be a significant performance detriment, and if the
        # autoscheduler models ever change, we'd like this constraint to still
        # be enforced (and plus this shows that we have explicitly thought
        # about this constraint.)

        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if scheduling the section starting at the given roomslot would
        violate the constraint, None otherwise."""
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
        return None

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if unscheduling the specified section will violate the constraint,
        None otherwise."""
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if swapping two sections will violate the constraint,
        None otherwise."""
        return None


class RoomConcurrencyConstraint(BaseConstraint):
    """Rooms can't be double-booked."""

    required = True  # A double-booked room will violate consistency checks.

    def check_schedule(self, schedule):
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""
        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if scheduling the section starting at the given roomslot would
        violate the constraint, None otherwise."""
        classroom = start_roomslot.room
        assigned_roomslots = classroom.get_roomslots_by_duration(
                start_roomslot, section.duration)
        if len(assigned_roomslots) == 0:
            return ConstraintViolation(
                self.__class__.__name__,
                "Section wouldn't be assigned any roomslots")
        for roomslot in assigned_roomslots:
            if roomslot.assigned_section is not None:
                return ConstraintViolation(
                    self.__class__.__name__,
                    "Room would be double-booked")
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
        classroom = start_roomslot.room
        assigned_roomslots = classroom.get_roomslots_by_duration(
                start_roomslot, section.duration)
        if len(assigned_roomslots) == 0:
            return ConstraintViolation(
                self.__class__.__name__,
                "Section wouldn't be assigned any roomslots")
        for roomslot in assigned_roomslots:
            if not (roomslot.assigned_section in [None, section]):
                return ConstraintViolation(
                    self.__class__.__name__,
                    "Room would be double-booked")
        return None

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if unscheduling the specified section will violate the constraint,
        None otherwise."""
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if swapping two sections will violate the constraint,
        None otherwise."""
        return None


class SectionDurationConstraint(BaseConstraint):
    """Sections must be scheduled for exactly their length.
    This also accounts for not scheduling a section twice,
    in conjunction with consistency constraints."""

    required = True  # I think some of the other constraints assume this.

    def check_schedule(self, schedule):
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""
        for section in schedule.class_sections.itervalues():
            if len(section.assigned_roomslots) != 0:
                start_time = section.assigned_roomslots[0].timeslot.start
                end_time = section.assigned_roomslots[-1].timeslot.end
                scheduled_duration = util.hours_difference(
                        start_time, end_time)
                if abs(scheduled_duration - section.duration) \
                        > config.DELTA_TIME:
                    return ConstraintViolation(
                        self.__class__.__name__,
                        ("Section {} is scheduled for {} hours but "
                         "should be scheduled for {} hours"
                         .format(section.id, scheduled_duration,
                                 section.duration)))
        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if scheduling the section starting at the given roomslot would
        violate the constraint, None otherwise."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        if len(roomslots) == 0:
            return ConstraintViolation(
                self.__class__.__name__,
                "Section wouldn't receive any roomslots")
        start_time = roomslots[0].timeslot.start
        end_time = roomslots[-1].timeslot.end
        scheduled_duration = util.hours_difference(
                start_time, end_time)

        if abs(scheduled_duration - section.duration) > config.DELTA_TIME:
            return ConstraintViolation(
                self.__class__.__name__,
                "Section would be scheduled for {} hours instead of {}"
                .format(scheduled_duration, section.duration))
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
        return self.check_schedule_section(section, start_roomslot, schedule)

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if unscheduling the specified section will violate the constraint,
        None otherwise."""
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if swapping two sections will violate the constraint,
        None otherwise."""
        return None


class TeacherAvailabilityConstraint(BaseConstraint):
    """Teachers can only teach during times they are available."""

    required = True  # I'm not sure if it actually is, but let's be safe.

    def check_schedule(self, schedule):
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""
        for teacher in schedule.teachers.itervalues():
            for section in teacher.taught_sections.itervalues():
                if len(section.assigned_roomslots) > 0:
                    for roomslot in section.assigned_roomslots:
                        start_time = roomslot.timeslot.start
                        end_time = roomslot.timeslot.end
                        if (start_time, end_time) \
                                not in teacher.availability_dict:
                            return ConstraintViolation(
                                self.__class__.__name__,
                                ("User {} is teaching from {} to {} but isn't "
                                 "available".format(
                                     teacher.id,
                                     str(start_time),
                                     str(end_time))))

        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if scheduling the section starting at the given roomslot would
        violate the constraint, None otherwise."""
        room = start_roomslot.room
        roomslots = room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        for teacher in section.teachers:
            for roomslot in roomslots:
                start_time = roomslot.timeslot.start
                end_time = roomslot.timeslot.end
                if (start_time, end_time) not in \
                        teacher.availability_dict:
                            return ConstraintViolation(
                                self.__class__.__name__,
                                "Teacher isn't available")
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
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
                            return ConstraintViolation(
                                self.__class__.__name__,
                                "Teacher isn't available")
        return None

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if unscheduling the specified section will violate the constraint,
        None otherwise."""
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if swapping two sections will violate the constraint,
        None otherwise."""
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
                            return ConstraintViolation(
                                self.__class__.__name__,
                                ("Teacher from first section won't "
                                 "be available"))

        for teacher in teachers2:
            for roomslot in roomslots1:
                start_time = roomslot.timeslot.start
                end_time = roomslot.timeslot.end
                if (start_time, end_time) not in teacher.availability_dict \
                        and (start_time, end_time) not in timeslots2:
                            return ConstraintViolation(
                                self.__class__.__name__,
                                ("Teacher from second section won't "
                                 "be available"))

        return None


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
        """Returns a ConstraintViolation if an AS_Schedule violates the constraint,
        None otherwise."""
        for teacher in schedule.teachers.itervalues():
            already_teaching = set()
            for section in teacher.taught_sections.itervalues():
                for roomslot in section.assigned_roomslots:
                    start_time = roomslot.timeslot.start
                    end_time = roomslot.timeslot.end
                    if (start_time, end_time) in already_teaching:
                        return ConstraintViolation(
                            self.__class__.__name__,
                            "Teacher id {} is teaching twice at once"
                            .format(teacher.id))
                    already_teaching.add((start_time, end_time))
        return None

    def check_schedule_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if scheduling the section starting at the given roomslot would
        violate the constraint, None otherwise."""
        for teacher in section.teachers:
            already_teaching = self.get_already_teaching_set(teacher)
            assigned_roomslots = start_roomslot.room.get_roomslots_by_duration(
                    start_roomslot, section.duration)
            for roomslot in assigned_roomslots:
                if (roomslot.timeslot.start, roomslot.timeslot.end) \
                        in already_teaching:
                            return ConstraintViolation(
                                self.__class__.__name__,
                                "Teacher is already teaching")
        return None

    def check_move_section(self, section, start_roomslot, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if moving the already-scheduled section to the given starting roomslot
        would violate the constraint, None otherwise."""
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
                            return ConstraintViolation(
                                self.__class__.__name__,
                                "Teacher is already teaching")

        return None

    def check_unschedule_section(self, section, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if unscheduling the specified section will violate the constraint,
        None otherwise."""
        return None

    def check_swap_sections(self, section1, section2, schedule):
        """Assuming that we start with a valid schedule, returns a ConstraintViolation
        if swapping two sections will violate the constraint,
        None otherwise."""
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
                    return ConstraintViolation(
                        self.__class__.__name__,
                        "Teacher in first section is already teaching")
        for teacher in section2.teachers:
            already_teaching = self.get_already_teaching_set(teacher)
            for time in timeslots1:
                if time in already_teaching and time not in timeslots2:
                    return ConstraintViolation(
                        self.__class__.__name__,
                        "Teacher in second section is already teaching")
        return None


def get_all_constraint_classes_dict():
    return {
        name: item for name, item in globals().iteritems()
        if inspect.isclass(item)
        and issubclass(item, BaseConstraint)
        and item not in [BaseConstraint, CompositeConstraint]}


def get_required_constraint_names():
    return [
        name for name, constraint in
        get_all_constraint_classes_dict().iteritems() if constraint.required]


def get_optional_constraint_names():
    return [
        name for name, constraint in
        get_all_constraint_classes_dict().iteritems() if not
        constraint.required]
