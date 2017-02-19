"""A controller for the autoscheduler."""

from esp.program.models import ClassSection
from esp.users.models import ESPUser
from esp.program.controllers.autoscheduler import \
    db_interface, constraints, config, manipulator, resource_checker, \
    search
from esp.program.controllers.autoscheduler.exceptions import SchedulingError


class AutoschedulerController(object):
    def __init__(self, prog, **options):
        self.options = options
        constraint_options = {
            k.split('_', 1)[1]: v for k, v in options.iteritems()
            if k.startswith("constraint_")}
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
        resource_constraints = resource_checker.create_resource_criteria(
                [{k: spec for k, (spec, wt) in resource_criteria.iteritems()
                  if resource_options[k] == -1}])
        resource_scorers = resource_checker.create_resource_criteria(
                [{k: (spec, resource_options[k])
                  for k, (spec, wt) in resource_criteria.iteritems()
                  if resource_options[k] != -1}])
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
        """Map from resource criterion name to (weight, spec). If criterion is
        required, mark as -1."""
        resource_criteria = load_all_resource_criteria(prog)
        resource_options = {k: (wt, spec) for k, (spec, wt)
                            in resource_criteria.iteritems()}
        return resource_options

    @staticmethod
    def search_options(prog):
        """Options for the searcher. Map from key to default value and
        description."""
        return {
            "section_emailcode":
                ("X1234s1", "Emailcode of the section to optimize."),
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
        for action in self.optimizer.manipulator.history:
            row = ["", []]
            if action["action"] == "schedule":
                row[0] = "Scheduled section:"
                row[1] += self.section_info(action["section"])
                row[1].append("<b>in room:</b>")
                row[1] += self.roomslot_info(action["start_roomslot"])
            elif action["action"] == "move":
                row[0] = "Moved section:"
                row[1] += self.section_info(action["section"])
                row[1].append("<b>From room:</b>")
                row[1] += self.roomslot_info(action["prev_start_roomslot"])
                row[1].append("<b>To room:</b>")
                row[1] += self.roomslot_info(action["start_roomslot"])
            elif action["action"] == "unschedule":
                row[0] = "Unscheduled section:"
                row[1] += self.section_info(action["section"])
                row[1].append("<b>From room:</b>")
                row[1] += self.roomslot_info(action["prev_start_roomslot"])
            elif action["action"] == "swap":
                row[0] = "Swapped sections:"
                sec1, sec2 = action["sections"]
                row[1] += self.section_info(sec1)
                row[1].append("<b>Now in room:</b>")
                row[1] += self.roomslot_info(sec1.assigned_roomslots[0])
                row[1].append("<b>And section:</b>")
                row[1] += self.section_info(sec2)
                row[1].append("<b>Now in room:</b>")
                row[1] += self.roomslot_info(sec2.assigned_roomslots[0])
            else:
                raise SchedulingError("History was broken.")
            rows.append(row)
        return rows

    def section_info(self, section):
        section_obj = ClassSection.objects.get(id=section.id)
        info = []
        info.append("Emailcode: {}".format(section_obj.emailcode()))
        info.append("ID: {}".format(section.id))
        info.append("Title: {}".format(section_obj.parent_class.title))
        info.append("Teachers:")
        for teacher in section.teachers:
            user = ESPUser.objects.get(id=teacher.id)
            info.append(user.name())
        info.append("Capacity: {}".format(section.capacity))
        info.append("Duration: {}".format(section.duration))
        info.append("Grades: {}-{}".format(
            section.grade_min, section.grade_max))
        info.append("Resource requests:")
        for restype in section.resource_requests.itervalues():
            if restype.value == "":
                info.append(restype.name)
            else:
                info.append("{}: {}".format(restype.name, restype.value))
        return info

    def roomslot_info(self, roomslot):
        info = []
        info.append(roomslot.room.name)
        info.append("Capacity: {}".format(roomslot.room.capacity))
        info.append("Furnishings:")
        for restype in roomslot.room.furnishings.itervalues():
            if restype.value == "":
                info.append(restype.name)
            else:
                info.append("{}: {}".format(restype.name, restype.value))
        info.append("Starting at time {}".format(roomslot.timeslot.start))
        return info

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


def load_all_resource_criteria(prog):
    resource_constraints = db_interface.load_resource_constraints(
            prog, specs_only=True)
    overrides = {k: (v, -1) for k, v in resource_constraints.iteritems()}
    resource_scoring = db_interface.load_resource_scoring(
            prog, overrides, specs_only=True)
    return resource_scoring


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
