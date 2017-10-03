"""A controller for the autoscheduler."""

from django.core.exceptions import ObjectDoesNotExist

from esp.program.models import ClassSection
from esp.users.models import ESPUser
from esp.resources.models import ResourceType
from esp.program.controllers.autoscheduler import \
    db_interface, constraints, config, manipulator, resource_checker, \
    search
from esp.program.controllers.autoscheduler.exceptions import SchedulingError


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
        if config.USE_TIMER:
            m.print_recorded_times()

    @staticmethod
    def constraint_options(prog):
        """Map from constraint names to (True/False, description)."""
        required_constraints = constraints.get_required_constraints()
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
                (1, "Depth to search."),
            "timeout":
                (3.0, "Timeout in seconds for the search."),
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
        self.optimizer.optimize_section(self.section, self.depth, self.timeout)

    def get_scheduling_info(self):
        rows = []
        for action in self.simplify_history(
                self.optimizer.manipulator.history):
            row = []
            if action["action"] == "schedule":
                row.append(["Scheduled {}:".format(
                                self.section_identifier(action["section"])),
                           self.section_info(action["section"])])
                row.append(["In {}:".format(
                                self.roomslot_identifier(
                                    action["start_roomslot"])),
                           self.roomslot_info(action["start_roomslot"])])
            elif action["action"] == "move":
                row.append(["Moved {}:".format(
                                self.section_identifier(action["section"])),
                           self.section_info(action["section"])])
                row.append(["From {}:".format(
                                self.roomslot_identifier(
                                    action["prev_start_roomslot"])),
                           self.roomslot_info(action["prev_start_roomslot"])])
                row.append(["To {}:".format(
                                self.roomslot_identifier(
                                    action["start_roomslot"])),
                           self.roomslot_info(action["start_roomslot"])])
            elif action["action"] == "unschedule":
                row.append(["Unscheduled {}:".format(
                                self.section_identifier(action["section"])),
                           self.section_info(action["section"])])
                row.append(["From {}:".format(
                                self.roomslot_identifier(
                                    action["prev_start_roomslot"])),
                           self.roomslot_info(action["prev_start_roomslot"])])
            elif action["action"] == "swap":
                sec1, sec2 = action["sections"]
                rs2, rs1 = action["original_roomslots"]
                row.append(["Swapped {}:".format(
                                self.section_identifier(sec1)),
                           self.section_info(sec1)])
                row.append(["Now in {}:".format(self.roomslot_identifier(rs1)),
                           self.roomslot_info(rs1)])
                row.append(["and {}:".format(
                                self.section_identifier(sec2)),
                           self.section_info(sec2)])
                row.append(["Now in {}:".format(self.roomslot_identifier(rs2)),
                           self.roomslot_info(rs2)])
            else:
                raise SchedulingError("History was broken.")
            rows.append(row)
        return rows

    def section_identifier(self, section):
        section_obj = ClassSection.objects.get(id=section.id)
        return "{}: {} (id: {})".format(
            section_obj.emailcode(), section_obj.parent_class.title,
            section.id)

    def section_info(self, section):
        info = []
        teachers_list = [ESPUser.objects.get(id=teacher.id).name()
                         for teacher in section.teachers]
        info.append("<b>Teachers:</b> {}".format(
            ", ".join(teachers_list)))
        info.append("<b>Capacity: </b>{}".format(section.capacity))
        info.append("<b>Duration: </b>{}".format(section.duration))
        info.append("<b>Grades: </b>{}-{}".format(
            section.grade_min, section.grade_max))
        resources = ""
        for restype in section.resource_requests.itervalues():
            resources += "<li>"
            if restype.value == "":
                resources += restype.name
            else:
                resources += "{}: {}".format(restype.name, restype.value)
            resources += "</li>"
        info.append("<b>Resource requests:</b><ul>{}</ul>".format(
            resources))
        return info

    def roomslot_identifier(self, roomslot):
        return "{} starting at {}".format(
                roomslot.room.name,
                roomslot.timeslot.start.strftime("%A %-I:%M%p"))

    def roomslot_info(self, roomslot):
        info = []
        info.append("<b>Capacity:</b> {}".format(roomslot.room.capacity))
        resources = ""
        for restype in roomslot.room.furnishings.itervalues():
            resources += "<li>"
            if restype.value == "":
                resources += restype.name
            else:
                resources += "{}: {}".format(restype.name, restype.value)
            resources += "</li>"
        info.append("<b>Furnishings:</b><ul>{}</ul>".format(
            resources))
        return info

    def simplify_history(self, history):
        """Given a history object, this simplifies it. It is NOT necessarily an
        equivalent object, but it should be more understandable, e.g. if you
        unschedule and reschedule a class, it will count as a move."""
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
        return [
            self.optimizer.manipulator.jsonify_history(),
            self.options]

    def import_assignments(self, data):
        print "Saving?"
        print data
        if not self.optimizer.manipulator.load_history(data):
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
            comment = "{}_comment".format(k)
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
                raise SchedulingError("Section not found.")
            return schedule.class_sections[section.id]
    raise SchedulingError("Section not found.")
