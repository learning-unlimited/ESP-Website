"""A controller for the automatic scheduling assistant."""

import datetime
import logging
from django.core.exceptions import ObjectDoesNotExist

from esp.program.models import ClassSection
from esp.users.models import ESPUser
from esp.resources.models import ResourceType
from esp.program.controllers.autoscheduler import \
    db_interface, constraints, config, manipulator, resource_checker, \
    search
from esp.program.controllers.autoscheduler.exceptions import SchedulingError

logger = logging.getLogger(__name__)


class AutoschedulerController(object):
    def __init__(self, prog, **options):
        self.options = options
        constraint_options = {
            k.split('_', 1)[1]: v for k, v in options.iteritems()
            if k.startswith("constraints_")}
        scoring_options = {
            k.split('_', 1)[1]: v for k, v in options.iteritems()
            if k.startswith("scorers_")}
        resource_options = {
            k.split('_', 1)[1]: v for k, v in options.iteritems()
            if k.startswith("resources_")}
        search_options = {
            k.split('_', 1)[1]: v for k, v in options.iteritems()
            if k.startswith("search_")}
        constraint_names = [k for k, v in constraint_options.iteritems()
                            if v]
        resource_criteria = load_all_resource_criteria(prog)
        valid_res_types = \
            ResourceType.objects.filter(program=prog).values_list(
                    "name", flat=True)
        resource_constraints = resource_checker.create_resource_criteria(
                [{k: spec for k, (spec, wt) in resource_criteria.iteritems()
                  if resource_options[k] == -1}], valid_res_types)
        resource_scorers = resource_checker.create_resource_criteria(
                [{k: (spec, resource_options[k])
                  for k, (spec, wt) in resource_criteria.iteritems()
                  if resource_options[k] != -1}], valid_res_types,
                use_weights=True)
        schedule = db_interface.load_schedule_from_db(
            prog, **search_options)
        m = manipulator.ScheduleManipulator(
                schedule, constraint_names=constraint_names,
                constraint_kwargs={"resource_criteria": resource_constraints},
                scorer_names_and_weights=scoring_options,
                scorer_kwargs={"resource_criteria": resource_scorers})
        self.optimizer = search.SearchOptimizer(m)
        self.depth = search_options["depth"]
        self.section = get_section_by_emailcode(
                search_options["section_emailcode"], schedule)
        self.timeout = search_options["timeout"]
        self.schedule = self.optimizer.manipulator.schedule
        self.initial_scores, self.initial_total_score = \
            self.optimizer.manipulator.scorer.get_all_score_schedule()
        if config.USE_TIMER:
            m.print_recorded_times()

    @staticmethod
    def constraint_options(prog):
        """Map from constraint names to (True/False, description)."""
        required_constraints = constraints.get_required_constraint_names()
        overrides = {c: "Required" for c in required_constraints}
        loaded_constraints = db_interface.load_constraints(prog, overrides)
        constraint_options = {
            k: (v, config.CONSTRAINT_DESCRIPTIONS[k])
            for k, v in loaded_constraints.iteritems()}
        return constraint_options

    @staticmethod
    def scorer_options(prog):
        """Map from scorer names to (weight, description)."""
        scorers = db_interface.load_scorers(prog)
        scorer_options = {
            k: (v, config.SCORER_DESCRIPTIONS[k])
            for k, v in scorers.iteritems()}
        return scorer_options

    @staticmethod
    def resource_options(prog):
        """Map from resource criterion name to (weight, spec_or_comment). If
        criterion is required, mark as -1."""
        resource_criteria = load_all_resource_criteria(prog, use_comments=True)
        resource_options = {k: (wt, spec) for k, (spec, wt)
                            in resource_criteria.iteritems()}
        return resource_options

    @staticmethod
    def search_options(prog, section=None):
        """Options for the searcher. Map from key to default value and
        description."""
        emailcode = "X1234s1"
        if section is not None and section.isdigit():
            try:
                section = ClassSection.objects.get(
                        id=int(section), parent_class__parent_program=prog)
                emailcode = section.emailcode()
            except ObjectDoesNotExist:
                pass
        return {
            "section_emailcode":
                (emailcode, "Emailcode of the section to optimize."),
            "depth":
                (1, "Depth to search. 1, 2, maybe 3 are okay, 4 is too slow."),
            "timeout":
                (10.0, "Timeout in seconds for the search."),
            "require_approved":
                (True, "Only schedule approved classes."),
            "exclude_lunch":
                (True, "Don't schedule lunch classes."),
            "exclude_walkins":
                (True, "Don't schedule walk-ins."),
            "exclude_scheduled":
                (False, "Don't touch already-scheduled classes."),
            "exclude_locked":
                (True, "Don't touch classes locked on the AJAX scheduler"),
        }

    def compute_assignments(self):
        self.optimizer.optimize_section(
                self.section, self.depth,
                datetime.datetime.now() +
                datetime.timedelta(seconds=self.timeout))

    def get_scheduling_info(self):
        rows = []
        for action in self.simplify_history(
                self.optimizer.manipulator.history):
            row = []
            if action["action"] == "schedule":
                row.append([u"Scheduled {}:".format(
                                self.section_identifier(action["section"])),
                           self.section_info(action["section"])])
                row.append([u"In {}:".format(
                                self.roomslot_identifier(
                                    action["start_roomslot"])),
                           self.roomslot_info(action["start_roomslot"])])
            elif action["action"] == "move":
                row.append([u"Moved {}:".format(
                                self.section_identifier(action["section"])),
                           self.section_info(action["section"])])
                row.append([u"From {}:".format(
                                self.roomslot_identifier(
                                    action["prev_start_roomslot"])),
                           self.roomslot_info(action["prev_start_roomslot"])])
                row.append([u"To {}:".format(
                                self.roomslot_identifier(
                                    action["start_roomslot"])),
                           self.roomslot_info(action["start_roomslot"])])
            elif action["action"] == "unschedule":
                row.append([u"Unscheduled {}:".format(
                                self.section_identifier(action["section"])),
                           self.section_info(action["section"])])
                row.append([u"From {}:".format(
                                self.roomslot_identifier(
                                    action["prev_start_roomslot"])),
                           self.roomslot_info(action["prev_start_roomslot"])])
            elif action["action"] == "swap":
                sec1, sec2 = action["sections"]
                rs2, rs1 = action["original_roomslots"]
                row.append([u"Swapped {}:".format(
                                self.section_identifier(sec1)),
                           self.section_info(sec1)])
                row.append([u"Now in {}:".format(
                                self.roomslot_identifier(rs1)),
                           self.roomslot_info(rs1)])
                row.append([u"and {}:".format(
                                self.section_identifier(sec2)),
                           self.section_info(sec2)])
                row.append([u"Now in {}:".format(
                                self.roomslot_identifier(rs2)),
                           self.roomslot_info(rs2)])
            else:
                raise SchedulingError("History was broken.")
            rows.append(row)
        if len(rows) > 0:
            final_scores, final_total_score = \
                self.optimizer.manipulator.scorer.get_all_score_schedule()
            diffs = []
            for (scorer, weight, old_score), (scorer2, weight2, new_score) in \
                    zip(self.initial_scores, final_scores):
                assert (scorer == scorer2), "Scorers changed"
                assert (weight == weight2), "Weights changed"
                diffs.append((
                    scorer, weight,
                    (new_score - old_score) * len(
                        self.schedule.class_sections)))
            # Sort descending by score change
            total_wt = sum([x[1] for x in diffs])
            diffs = sorted(diffs, key=lambda x: -x[2] * x[1])
            total_change = (final_total_score - self.initial_total_score) \
                * len(self.schedule.class_sections)

            def format_row(row):
                scorer, weight, delta = row
                return u"{} (wt {}): chg {:.3f} -> {:.3f}".format(
                    scorer, weight, delta, weight * delta / total_wt)
            new_row = []
            if len(diffs) > 6:
                new_row += [format_row(r) for r in diffs[:3]]
                new_row += [u"[{} more truncated]".format(len(diffs) - 6)]
                new_row += [format_row(r) for r in diffs[-3:]]
            else:
                new_row += [format_row(r) for r in diffs]
            new_row += [u"Total change: {}".format(total_change)]
            rows.append([[
                "Major score changes (weight, change, contribution):",
                new_row]])
        return rows

    def section_identifier(self, section):
        section_obj = ClassSection.objects.get(id=section.id)
        manage = "/manage/{}/manageclass/{}".format(
            section_obj.parent_class.parent_program.getUrlBase(),
            section.parent_class)
        manage_link = "<a href='{}'>Manage</a>".format(manage)
        edit = "/manage/{}/editclass/{}".format(
            section_obj.parent_class.parent_program.getUrlBase(),
            section.parent_class)
        edit_link = "<a href='{}'>Edit</a>".format(edit)
        return u"{}: {} (id: {}) ({}, {})".format(
            section_obj.emailcode(), section_obj.parent_class.title,
            section.id, manage_link, edit_link)

    def section_info(self, section):
        info = []
        teachers_list = [ESPUser.objects.get(id=teacher.id).name()
                         for teacher in section.teachers]
        info.append(u"<b>Teachers:</b> {}".format(
            ", ".join(teachers_list)))
        info.append(u"<b>Capacity: </b>{}".format(section.capacity))
        info.append(u"<b>Duration: </b>{}".format(section.duration))
        info.append(u"<b>Grades: </b>{}-{}".format(
            section.grade_min, section.grade_max))
        resources = ""
        for restype in section.resource_requests.itervalues():
            resources += "<li>"
            if restype.value == "":
                resources += restype.name
            else:
                resources += u"{}: {}".format(restype.name, restype.value)
            resources += "</li>"
        info.append(u"<b>Resource requests:</b><ul>{}</ul>".format(
            resources))
        cls = ClassSection.objects.get(id=section.id).parent_class
        info.append(u"<b>Class Flags: </b>{}".format(u", ".join(
            cls.flags.values_list(
                'flag_type__name', flat=True))))
        return info

    def roomslot_identifier(self, roomslot):
        return u"{} starting at {}".format(
                roomslot.room.name,
                roomslot.timeslot.start.strftime("%A %-I:%M%p"))

    def roomslot_info(self, roomslot):
        info = []
        info.append(u"<b>Capacity:</b> {}".format(roomslot.room.capacity))
        resources = ""
        for restype in roomslot.room.furnishings.itervalues():
            resources += "<li>"
            if restype.value == "":
                resources += restype.name
            else:
                resources += u"{}: {}".format(restype.name, restype.value)
            resources += "</li>"
        info.append(u"<b>Furnishings:</b><ul>{}</ul>".format(
            resources))
        return info

    def simplify_history(self, history):
        """Given a history object, this simplifies it. It is NOT necessarily an
        equivalent object, but it should be more understandable, e.g. if you
        unschedule and reschedule a class, it will count as a move. In
        particular, although in a sense the simplified history is semantically
        equivalent, the simplified history may not be executable. For example,
        when executing a 3-way cycle of classes, the original history may
        unschedule all 3 first and then reschedule all 3 in their new slots,
        but the simplified history will have 3 moves, all of which will fail
        because the destination is occupied."""
        # Dict mapping from section to [original_roomslot, final_roomslot]
        sections = {}
        for action in history:
            if action["action"] == "schedule":
                section = action["section"]
                if section not in sections:
                    sections[section] = [None, action["start_roomslot"]]
                else:
                    sections[section][1] = action["start_roomslot"]
            elif action["action"] == "move":
                section = action["section"]
                if section not in sections:
                    sections[section] = [
                        action["prev_start_roomslot"],
                        action["start_roomslot"]]
                else:
                    sections[section][1] = action["start_roomslot"]
            elif action["action"] == "unschedule":
                section = action["section"]
                if section not in sections:
                    sections[section] = [action["prev_start_roomslot"], None]
                else:
                    sections[section][1] = None
            elif action["action"] == "swap":
                # This loop iterates over exactly two sections.
                for section, old_r, new_r in zip(
                        action["sections"], action["original_roomslots"],
                        reversed(action["original_roomslots"])):
                    if section not in sections:
                        sections[section] = [old_r, new_r]
                    else:
                        sections[section][1] = new_r
        new_history = []
        for section, (old_r, new_r) in sections.iteritems():
            if old_r is None:
                assert new_r is not None, "Did nothing"
                new_history.append({
                    "action": "schedule",
                    "section": section,
                    "start_roomslot": new_r,
                })
            else:
                if new_r is None:
                    new_history.append({
                        "action": "unschedule",
                        "section": section,
                        "prev_start_roomslot": old_r,
                    })
                else:
                    new_history.append({
                        "action": "move",
                        "section": section,
                        "start_roomslot": new_r,
                        "prev_start_roomslot": old_r,
                    })
        return new_history

    def export_assignments(self):
        changed_sections = set()
        for action in self.optimizer.manipulator.history:
            changed_sections.add(action["section"])
        scheduling_hashes = {
            section.id: section.initial_state for section in changed_sections}
        logger.info(scheduling_hashes)
        return [
            [self.optimizer.manipulator.jsonify_history(), scheduling_hashes],
            self.options]

    def import_assignments(self, data):
        history, scheduling_hashes = data
        logger.info(scheduling_hashes)
        for section, scheduling_hash in scheduling_hashes.iteritems():
            initial_state = self.schedule.class_sections[
                int(section)].initial_state
            logger.info(initial_state)
            if initial_state != scheduling_hash:
                emailcode = ClassSection.objects.get(
                        id=int(section)).emailcode()
                raise SchedulingError(
                    u"Section {} was moved.".format(emailcode))
        if not self.optimizer.manipulator.load_history(history):
            raise SchedulingError("Unable to replay assignments.")

    def save_assignments(self):
        db_interface.save(self.optimizer.manipulator.schedule)


def load_all_resource_criteria(prog, use_comments=False):
    """If use_comments is true, we load comments (where available) instead
    of specs."""
    resource_constraints = db_interface.load_resource_constraints(
            prog, specs_only=True, ignore_comments=(not use_comments))
    overrides = {k: (v, -1) for k, v in resource_constraints.iteritems()}
    resource_criteria = db_interface.load_resource_scoring(
            prog, overrides, specs_only=True,
            ignore_comments=(not use_comments))
    if use_comments:
        for k in resource_criteria:
            comment = u"{}_comment".format(k)
            if comment in resource_criteria:
                resource_criteria[k] = \
                    (resource_criteria[comment][0], resource_criteria[k][1])
    return {k: v for k, v in resource_criteria.iteritems() if "_comment" not in
            k}


def get_section_by_emailcode(emailcode, schedule):
    # This is inefficient but whatever, we're loading the whole program anyway.
    sections = ClassSection.objects.filter(
            parent_class__parent_program=schedule.program)
    for section in sections:
        if section.emailcode() == emailcode:
            if section.id not in schedule.class_sections:
                raise SchedulingError(
                        "Scheduler can't handle this section. This may "
                        "be because it's locked, unapproved, scheduled "
                        "weirdly, or otherwise excluded from sections "
                        "the assistant is allowed to touch.")
            return schedule.class_sections[section.id]
    raise SchedulingError("Section not found.")
