"""
A schedule manipulator. Stores and makes changes to an AS_schedule.
"""


class ScheduleManipulator:
    def __init__(self, schedule, constraints=None):
        self.schedule = schedule
        self.constraints = constraints if constraints is not None else \
            schedule.constraints

    def schedule_section(self, section, start_roomslot):
        """Schedules the given section starting at the given roomslot;
        returns True if successful, False if not. Iterates over the roomslot's
        room's availabilities until it has a sufficient length."""
        if section.is_scheduled():
            return False

        if not self.constraints.check_schedule_section(
                section, start_roomslot, self.schedule):
            return False

        roomslots_to_use = start_roomslot.room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        section.assign_roomslots(roomslots_to_use)
        return True

    def move_section(self, section, start_roomslot):
        """Moves an already-scheduled section to a different given roomslot;
        returns True if successful, False if not. Has the same behavior as
        schedule_section for multi-hour classes."""
        if not section.is_scheduled():
            return False

        if not self.constraints.check_move_section(
                section, start_roomslot, self.schedule):
            return False

        section.clear_roomslots()
        roomslots_to_use = start_roomslot.room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        section.assign_roomslots(roomslots_to_use)

    def unschedule_section(self, section):
        """Unschedules an already_scheduled section. Returns True if successful,
        False if not."""
        if not section.is_scheduled():
            return False

        if not self.constraints.check_unschedule_section(
                section, self.schedule):
            return False

        section.clear_roomslots()

    def swap_sections(self, section1, section2):
        """Swaps two already-scheduled sections of the same duration. Returns
        True if successful, False if not."""
        if not (section1.is_scheduled() and section2.is_scheduled()):
            return False

        if section1.duration != section2.duration:
            return False

        if not self.constraints.check_swap_sections(
                section1, section2, self.schedule):
            return False

        roomslots1 = section1.assigned_roomslots
        roomslots2 = section2.assigned_roomslots
        section1.assign_roomslots(roomslots2, clear_existing=True)
        section2.assign_roomslots(roomslots1)
