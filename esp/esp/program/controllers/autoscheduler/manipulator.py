"""
A schedule manipulator. Stores and makes changes to an AS_schedule.
"""

from esp.program.controllers.autoscheduler.scoring import CompositeScorer
from esp.program.controllers.autoscheduler.constraints import \
    CompositeConstraint
from esp.program.controllers.autoscheduler import util


class ScheduleManipulator:
    """Class which stores a schedule and contains functions for modifying it
    subject to a particular set of constraints. Can optionally hold a scorer to
    keep updated."""
    def __init__(self, schedule, constraint_names=None, constraint_kwargs={},
                 scorer_names_and_weights={}, scorer_kwargs={}):
        """Initializes with the given schedule, and uses given constraint names
        and scorer names and weights (if provided)."""
        self.schedule = schedule
        self.constraints = CompositeConstraint(
                constraint_names, **constraint_kwargs) \
            if constraint_names is not None else schedule.constraints
        self.scorer = CompositeScorer(
                scorer_names_and_weights, schedule, **scorer_kwargs)

        # History of actions taken. Also contains enough additional information
        # for actions to be undone. Each record is a dict containing an
        # "action" key mapping to "schedule", "move", "unschedule", or "swap",
        # as well as whatever other information is relevant to either the
        # action or to undoing it.
        self.history = []

    def schedule_section(self, section, start_roomslot, force=False):
        """Schedules the given section starting at the given roomslot;
        returns True if successful, False if not. Iterates over the roomslot's
        room's availabilities until it has a sufficient length."""
        if not force:
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

    def move_section(self, section, start_roomslot, force=False):
        """Moves an already-scheduled section to a different given roomslot;
        returns True if successful, False if not. Has the same behavior as
        schedule_section for multi-hour classes."""
        if not force:
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

    def unschedule_section(self, section, force=False):
        """Unschedules an already_scheduled section. Returns True if successful,
        False if not."""
        if not force:
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

    def swap_sections(self, section1, section2, force=False):
        """Swaps two already-scheduled sections of the same duration. Returns
        True if successful, False if not."""
        if not force:
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
                success = self.unschedule_section(
                        last_action["section"], force=True)
                assert success, "Undo failed"
            elif last_action["action"] == "move":
                success = self.move_section(
                        last_action["section"],
                        last_action["prev_start_roomslot"],
                        force=True)
                assert success, "Undo failed"
            elif last_action["action"] == "unschedule":
                success = self.schedule_section(
                        last_action["section"],
                        last_action["prev_start_roomslot"],
                        force=True)
                assert success, "Undo failed"
            elif last_action["action"] == "swap":
                success = self.swap_sections(
                        *last_action["sections"],
                        force=True)
                assert success, "Undo failed"
            else:
                assert False, "Undo history had invalid action"
            # Pop history again because we just added the undo action to it.
            self.history.pop()
            return True

    def perform_action(self, action):
        """Performs the given action, as specified in the same way as
        history (though possibly without extraneous undo-ing information)."""
        if action["action"] == "schedule":
            return self.schedule_section(
                    action["section"], action["start_roomslot"])
        elif action["action"] == "move":
            return self.move_section(action["section"],
                                     action["start_roomslot"])
        elif action["action"] == "unschedule":
            return self.unschedule_section(action["section"])
        elif action["action"] == "swap":
            return self.swap_sections(*action["sections"])

    def jsonify_action(self, action):
        """Turns an action (i.e. history item) into a json-like dict."""
        jsonified_dict = {"action": action["action"]}
        if "section" in action:
            jsonified_dict["section"] = action["section"].id
        if "start_roomslot" in action:
            roomslot = action["start_roomslot"]
            jsonified_dict["start_roomslot"] = [
                [util.datetimedump(roomslot.timeslot.start),
                 util.datetimedump(roomslot.timeslot.end)],
                roomslot.room.name]
        if "prev_start_roomslot" in action:
            roomslot = action["prev_start_roomslot"]
            jsonified_dict["prev_start_roomslot"] = [
                [util.datetimedump(roomslot.timeslot.start),
                 util.datetimedump(roomslot.timeslot.end)],
                roomslot.room.name]
        if "sections" in action:
            jsonified_dict["sections"] = [s.id for s in action["sections"]]
        return jsonified_dict

    def dejsonify_action(self, jsonified_dict):
        """Turns a json-like action into an action."""
        action = {"action": jsonified_dict["action"]}
        if "section" in jsonified_dict:
            action["section"] = self.schedule.class_sections[
                    jsonified_dict["section"]]
        if "start_roomslot" in jsonified_dict:
            (start, end), room_name = jsonified_dict["start_roomslot"]
            times = (util.datetimeloads(start), util.datetimeloads(end))
            room = self.schedule.classrooms[room_name]
            action["start_roomslot"] = room.availability_dict[times]
        if "prev_start_roomslot" in jsonified_dict:
            (start, end), room_name = jsonified_dict["prev_start_roomslot"]
            times = (util.datetimeloads(start), util.datetimeloads(end))
            room = self.schedule.classrooms[room_name]
            action["prev_start_roomslot"] = room.availability_dict[times]
        if "sections" in jsonified_dict:
            action["sections"] = [
                self.schedule.class_sections[s_id] for s_id in
                jsonified_dict["sections"]]
        return action

    def jsonify_history(self):
        return [self.jsonify_action(action) for action in self.history]

    def load_history(self, jsonified_dicts):
        actions = [self.dejsonify_action(d) for d in jsonified_dicts]
        for action in actions:
            if not self.perform_action(action):
                return False
        return True

    def get_recorded_times(self):
        """Gets the times recorded, not necessarily by this manipulator."""
        return util.TIMES
