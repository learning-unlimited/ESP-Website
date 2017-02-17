"""
A schedule manipulator. Stores and makes changes to an AS_schedule.
"""

from esp.program.controllers.autoscheduler.scoring import CompositeScorer
from esp.program.controllers.autoscheduler.constraints import \
    CompositeConstraint


class ScheduleManipulator:
    """Class which stores a schedule and contains functions for modifying it
    subject to a particular set of constraints. Can optionally hold a scorer to
    keep updated."""
    def __init__(self, schedule, constraint_names=None,
                 scorer_names_and_weights=()):
        """Initializes with the given schedule, and uses given constraint names
        and scorer names and weights (if provided)."""
        self.schedule = schedule
        self.constraints = CompositeConstraint(constraint_names) \
            if constraint_names is not None else schedule.constraints
        self.scorer = CompositeScorer(scorer_names_and_weights, schedule)

        # History of actions taken. Also contains enough additional information
        # for actions to be undone. Each record is a dict containing an
        # "action" key mapping to "schedule", "move", "unschedule", or "swap",
        # as well as whatever other information is relevant to either the
        # action or to undoing it.
        self.history = []

    def schedule_section(self, section, start_roomslot):
        """Schedules the given section starting at the given roomslot;
        returns True if successful, False if not. Iterates over the roomslot's
        room's availabilities until it has a sufficient length."""
        if section.is_scheduled():
            return False

        if self.constraints.check_schedule_section(
                section, start_roomslot, self.schedule):
            return False

        self.history.append({
            "action": "schedule",
            "section": section,
            "start_roomslot": start_roomslot,
        })

        self.scorer.update_schedule_section(section, start_roomslot)
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

        if self.constraints.check_move_section(
                section, start_roomslot, self.schedule):
            return False

        self.history.append({
            "action": "move",
            "section": section,
            "start_roomslot": start_roomslot,
            "prev_start_roomslot": section.assigned_roomslots[0],
        })
        self.scorer.update_move_section(section, start_roomslot)
        section.clear_roomslots()
        roomslots_to_use = start_roomslot.room.get_roomslots_by_duration(
                start_roomslot, section.duration)
        section.assign_roomslots(roomslots_to_use)
        return True

    def unschedule_section(self, section):
        """Unschedules an already_scheduled section. Returns True if successful,
        False if not."""
        if not section.is_scheduled():
            return False

        if self.constraints.check_unschedule_section(
                section, self.schedule):
            return False

        self.history.append({
            "action": "unschedule",
            "section": section,
            "prev_start_roomslot": section.assigned_roomslots[0],
        })
        self.scorer.update_unschedule_section(section)
        section.clear_roomslots()
        return True

    def swap_sections(self, section1, section2):
        """Swaps two already-scheduled sections of the same duration. Returns
        True if successful, False if not."""
        if not (section1.is_scheduled() and section2.is_scheduled()):
            return False

        if section1.duration != section2.duration:
            return False

        if self.constraints.check_swap_sections(
                section1, section2, self.schedule):
            return False

        self.history.append({
            "action": "swap",
            "sections": (section1, section2),
        })
        self.scorer.update_swap_sections(section1, section2)
        roomslots1 = section1.assigned_roomslots
        roomslots2 = section2.assigned_roomslots
        section1.assign_roomslots(roomslots2, clear_existing=True)
        section2.assign_roomslots(roomslots1)
        return True

    def undo(self):
        """Undoes the last action. Returns True if there was anything to undo.
        """
        if len(self.history) == 0:
            # Nothing to undo.
            return False
        else:
            last_action = self.history.pop()
            if last_action["action"] == "schedule":
                self.unschedule_section(last_action["section"])
            elif last_action["action"] == "move":
                self.move_section(last_action["section"],
                                  last_action["prev_start_roomslot"])
            elif last_action["action"] == "unschedule":
                self.schedule_section(last_action["section"],
                                      last_action["prev_start_roomslot"])
            elif last_action["action"] == "swap":
                self.swap_sections(*last_action["sections"])
            else:
                assert False, "Undo history had invalid action"
            return True
