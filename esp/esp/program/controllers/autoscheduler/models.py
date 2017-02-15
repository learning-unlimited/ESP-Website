
"""Models for the autoscheduler. Mostly reflects the database on the rest of
the website, but having separate models should be a bit more robust to changes
in website structure and should also be more performant.
"""

from functools import total_ordering
import hashlib
import json

from django.db import transaction

from esp.program.controllers.autoscheduler.consistency_checks import \
        ConsistencyChecker
from esp.program.controllers.autoscheduler.exceptions import \
        ConsistencyError, SchedulingError
import esp.program.controllers.autoscheduler.constants as constants
from esp.program.controllers.autoscheduler.constraints import \
        CompositeConstraint
from esp.resources.models import ResourceType, Resource
from esp.program.models import ClassSection
from esp.users.models import ESPUser
from esp.cal.models import Event


class AS_Schedule:
    def __init__(self, program=None, timeslots=None, class_sections=None,
                 teachers=None, classrooms=None, lunch_timeslots=None,
                 required_resource_criteria=None, constraints=None):
        """Argument types:
         - program is a Program object
         - timeslots is a sorted list of AS_Timeslots
         - class_sections is a dict of {section_id: AS_ClassSection}
         - teachers is a dict of {teacher_id: AS_Teacher}
         - classrooms is a dict of {classroom_name: AS_Classroom}
         - lunch_timeslots is a list of (lunch_start, lunch_end).
         - constraints is a subclass of BaseConstraint (e.g.
           CompositeConstraint)
        """
        self.program = program
        self.timeslots = timeslots if timeslots is not None else []

        # Maps from start and end times to a timeslot.
        self.timeslot_dict = {(t.start, t.end): t for t in self.timeslots}
        # Dict of class sections by ID
        self.class_sections = class_sections if class_sections is not None \
            else {}
        # Dict of teachers by ID
        self.teachers = teachers if teachers is not None else {}
        # Dict of classrooms by name
        self.classrooms = classrooms if classrooms is not None else {}
        # A dict of lunch timeslots by day, i.e maps from (year, month, day)
        # to a list of timeslots. Timeslots should also be in timeslot_dict.
        self.lunch_timeslots = self.build_lunch_timeslots(
                lunch_timeslots if lunch_timeslots is not None else [])
        # A list of ResourceCriterions which are required (i.e. constraining).
        self.required_resource_criteria = required_resource_criteria \
            if required_resource_criteria is not None else []

        self.constraints = constraints if constraints is not None else \
            CompositeConstraint([])

        self.run_consistency_checks()
        self.run_constraint_checks()

    def build_lunch_timeslots(self, lunch_timeslots):
        timeslots_by_day = {}
        for (start, end) in lunch_timeslots:
            if (start, end) not in self.timeslot_dict:
                continue
            day = (start.year, start.month, start.day)
            assert (end.year, end.month, end.day) == day, \
                "Timeslot spans multiple days"
            timeslots_by_day.get(day, []).append(
                    self.timeslot_dict[(start, end)])
        return timeslots_by_day

    @staticmethod
    def load_from_db(
            program, require_approved=True, exclude_lunch=True,
            exclude_walkins=True, exclude_scheduled=True):
        ESPUser.create_membership_methods()

        timeslots = \
            sorted(AS_Timeslot.batch_convert(program.getTimeSlots(), program))

        lunch_events = Event.objects.filter(
                meeting_times__parent_class__category__category="Lunch",
                meeting_times__parent_class__parent_program=program)

        lunch_timeslots = [(e.start, e.end) for e in lunch_events]

        schedule = AS_Schedule(program=program, timeslots=timeslots,
                               lunch_timeslots=lunch_timeslots)

        schedule.class_sections, schedule.teachers, schedule.classrooms = \
            schedule.load_sections_and_teachers_and_classrooms(
                require_approved, exclude_lunch,
                exclude_walkins, exclude_scheduled)

        return schedule

    def load_sections_and_teachers_and_classrooms(
            self, require_approved, exclude_lunch,
            exclude_walkins, exclude_scheduled):
        """Loads the program's approved and unscheduled sections from db, and
        registers all teachers into the dict of teachers"""

        # Get all the approved class sections for the program
        all_sections = ClassSection.objects.filter(
                parent_class__parent_program=self.program,
                ).select_related()

        # We create a list of sections and a dict mapping from rooms to
        # timeslots when they aren't available due to already-scheduled
        # sections.
        sections = []
        exclude_availabilities = {}
        for section in all_sections:
            exclude = (
              (require_approved and section.status != 10)
              or (exclude_scheduled and len(section.get_meeting_times()) > 0)
              or (exclude_lunch and
                  section.parent_class.category.category == "Lunch")
              or (exclude_walkins and section.parent_class.category ==
                  self.program.open_class_category)
            )
            if exclude:
                for c in section.classrooms():
                    if c.name not in exclude_availabilities:
                        exclude_availabilities[c.name] = set()
                    exclude_availabilities[c.name].update(
                        [ts.id for ts in section.get_meeting_times()])
            else:
                sections.append(section)

        # For all excluded sections, remove their availabilities

        teachers = {}

        converted_sections = AS_ClassSection.batch_convert(
            sections, self.program, teachers, self.timeslot_dict)

        sections_dict = {sec.id: sec for sec in converted_sections}
        # Load classrooms from groupedClassrooms
        classrooms = AS_Classroom.batch_convert(
                self.program.groupedClassrooms(), self.program,
                self.timeslot_dict, exclude_availabilities)
        classrooms_dict = {room.name: room for room in classrooms}

        # Return!
        return sections_dict, teachers, classrooms_dict

    def save(self, check_consistency=True, check_constraints=True):
        """Saves the schedule."""
        if check_consistency:
            # Run a consistency check first.
            try:
                self.run_consistency_checks()
            except ConsistencyError:
                raise  # TODO
        if check_constraints:
            # Run a constraint check first.
            try:
                self.run_constraint_checks()
            except ConsistencyError:
                raise  # TODO

        # Find all sections which we've actually moved.
        changed_sections = set(
            [section for section in self.class_sections.itervalues()
             if section.initial_state
             != section.scheduling_hash()])
        # These are all the sections we are okay changing.
        unscheduled_sections = set()  # Sections we unscheduled temporarily
        with transaction.atomic():
            for section in changed_sections:
                section_obj = ClassSection.objects.get(id=section.id)
                print("Saving {}".format(section_obj.emailcode()))
                # Make sure nobody else touched the section
                if section.id in unscheduled_sections:
                    # Ensure the section is in fact unscheduled.
                    if len(section_obj.get_meeting_times()) > 0 \
                            or len(section_obj.classrooms()) > 0:
                        raise SchedulingError("Someone else moved a section.")
                else:
                    self.ensure_section_not_moved(section_obj, section)
                start_time = section.assigned_roomslots[0].timeslot.start
                end_time = section.assigned_roomslots[-1].timeslot.end
                # Make sure the teacher is available
                for teacher in section.teachers:
                    teacher_obj = ESPUser.objects.get(id=teacher.id)
                    other_sections = \
                        teacher_obj.getTaughtSections(self.program)
                    for other_section in other_sections:
                        conflict = False
                        for other_time in other_section.get_meeting_times():
                            if not (other_time.start >= end_time
                                    or other_time.end <= start_time):
                                conflict = True
                                break
                        if conflict:
                            err_msg = (
                                "Teacher {} is already teaching "
                                "from {} to {}".format(
                                    teacher.id,
                                    str(other_time.start),
                                    str(other_time.end)))
                            self.try_unschedule_section(
                                other_section,
                                unscheduled_sections,
                                err_msg)

                # Compute our meeting times and classroom
                meeting_times = Event.objects.filter(
                        id__in=[roomslot.timeslot.id
                                for roomslot in section.assigned_roomslots])
                initial_room_num = section.assigned_roomslots[0].room.name
                assert all([roomslot.room.name == initial_room_num
                            for roomslot in section.assigned_roomslots]), \
                    "Section was assigned to multiple rooms"

                room_objs = Resource.objects.filter(
                        name=initial_room_num,
                        res_type__name="Classroom",
                        event__in=meeting_times)

                # Make sure the room is available
                for room_obj in room_objs:
                    if room_obj.is_taken():
                        occupiers = room_obj.assignments()
                        for occupier in occupiers:
                            other_section = occupier.target
                            self.try_unschedule_section(
                                    other_section,
                                    unscheduled_sections,
                                    "Room is occupied")

                # Schedule the section!
                section_obj.assign_meeting_times(meeting_times)
                status, errors = section_obj.assign_room(room_objs[0])
                if not status:
                    section_obj.clear_meeting_times()
                    raise SchedulingError(
                            "Room assignment failed with errors: "
                            + " | ".join(errors))

                # Update the section's initial_state so we don't confuse
                # ourselves
                section.initial_state = section.scheduling_hash()

    def try_unschedule_section(self, section, unscheduled_sections,
                               error_message):
        """Tries to unschedule the given ClassSection. If it's not in the list
        of known sections (sections_by_id), throw a SchedulingError with the
        given error message. Otherwise, make sure the section wasn't moved by
        external sources, and unschedule it."""
        if section.id not in self.class_sections:
            raise SchedulingError(error_message)
        else:
            AS_Schedule.ensure_section_not_moved(
                    section, self.class_sections[section.id])
            AS_Schedule.unschedule_section(section, unscheduled_sections)

    def run_consistency_checks(self):
        ConsistencyChecker().run_all_consistency_checks(self)

    def run_constraint_checks(self):
        if not self.constraints.check_schedule(self):
            raise SchedulingError("Schedule violated constraints")

    @staticmethod
    def ensure_section_not_moved(section, as_section):
        """Ensures that a ClassSection hasn't moved, according to the record
        stored in its corresponding AS_Section. Raises a SchedulingError if it
        was moved, otherwise does nothing."""
        assert section.id == as_section.id, "Unexpected ID mismatch"
        if AS_ClassSection.scheduling_hash_of(section) \
                != as_section.initial_state:
            raise SchedulingError("Section {} was \
                    moved.".format(section.emailcode))

    @staticmethod
    def unschedule_section(section, unscheduled_sections_log=None):
        """Unschedules a ClassSection and records it as needed."""
        # Unschedule the offending section.
        section.clear_meeting_times()
        section.clearRooms()
        if unscheduled_sections_log is not None:
            unscheduled_sections_log.add(section.id)


class AS_ClassSection:
    def __init__(self, teachers, duration, capacity,
                 category, assigned_roomslots,
                 section_id=0, grade_min=7, grade_max=12,
                 resource_requests=None):
        self.id = section_id
        # Duration, in hours.
        self.duration = duration
        # A list of teachers.
        self.teachers = teachers
        # Capacity, an int.
        self.capacity = capacity
        # Min and max grade, integers
        self.grade_min = grade_min
        self.grade_max = grade_max
        # Category ID
        self.category = category
        # A sorted list of assigned roomslots.
        self.assigned_roomslots = assigned_roomslots
        # Dict from restype names to AS_Restypes requested
        self.resource_requests = resource_requests \
            if resource_requests is not None else {}

        # A hash of the initial state.
        self.initial_state = self.scheduling_hash()
        self.register_teachers()

    @staticmethod
    def convert_from_classection_obj(
            section, program, teachers_dict, timeslot_dict):
        """Create a AS_ClassSection from a ClassSection and Program. Will also
        populate the given dictionary of teachers and uses the given dictionary
        of timeslots for availabilities."""
        assert section.parent_class.parent_program == program

        teachers = []
        for teacher in section.teachers:
            if teacher.id not in teachers_dict:
                teachers_dict[teacher.id] = AS_Teacher.convert_from_espuser(
                        teacher, program, timeslot_dict)
            teachers.append(teachers_dict[teacher.id])

        resource_requests = AS_ResourceType.batch_convert_resource_requests(
                section.getResourceRequests())

        resource_requests_dict = {r.name: r for r in resource_requests}

        assert len(section.meeting_times.all()) == 0, "Already-scheduled sections \
            aren't supported yet"

        as_section = AS_ClassSection(
                teachers, float(section.duration), section.capacity,
                section.category.id, [],
                section_id=section.id,
                grade_min=section.parent_class.grade_min,
                grade_max=section.parent_class.grade_max,
                resource_requests=resource_requests_dict)

        assert as_section.scheduling_hash_of(section) == \
            as_section.initial_state, \
            "AS_ClassSection state doesn't match ClassSection state"

        return as_section

    def register_teachers(self):
        """Makes sure that all teachers have this section listed in their taught
        sections."""
        for teacher in self.teachers:
            teacher.taught_sections[self.id] = self

    def assign_roomslots(self, roomslots, clear_existing=False):
        if not clear_existing:
            assert self.assigned_roomslots == [], \
                    "Already assigned to roomslots"
        else:
            self.clear_roomslots()
        self.assigned_roomslots = sorted(roomslots, key=lambda r: r.timeslot)
        for roomslot in self.assigned_roomslots:
            assert roomslot.assigned_section is None, \
                    "Roomslot is occupied"
            roomslot.assigned_section = self

    def clear_roomslots(self):
        for roomslot in self.assigned_roomslots:
            roomslot.assigned_section = None
        self.assigned_roomslots = []

    def is_scheduled(self):
        return len(self.assigned_roomslots) > 0

    def scheduling_hash(self):
        """Creates a unique hash based on the timeslots and rooms assigned to
        this section."""
        meeting_times = sorted([(str(e.timeslot.start), str(e.timeslot.end))
                                for e in self.assigned_roomslots])
        rooms = sorted(list(set([r.room.name for r in
                                self.assigned_roomslots])))
        state_str = json.dumps([meeting_times, rooms])
        return hashlib.md5(state_str).hexdigest()

    @staticmethod
    def batch_convert(sections, program, teachers_dict, timeslot_dict):
        return map(lambda s: AS_ClassSection.convert_from_classection_obj(
            s, program, teachers_dict, timeslot_dict), sections)

    @staticmethod
    def scheduling_hash_of(section):
        """Creates a unique hash based on the timeslots and rooms assigned to a
        section."""
        meeting_times = sorted([(str(e.start), str(e.end))
                                for e in section.get_meeting_times()])
        rooms = sorted([r.name for r in section.classrooms()])
        state_str = json.dumps([meeting_times, rooms])
        return hashlib.md5(state_str).hexdigest()


class AS_Teacher:
    def __init__(self, availability, teacher_id=0, is_admin=False):
        self.id = teacher_id
        self.availability = availability if availability is not None \
            else []
        # Dict from section ID to section
        self.taught_sections = {}
        self.is_admin = is_admin
        self.availability_dict = {}
        for timeslot in self.availability:
            self.availability_dict[(
                timeslot.start, timeslot.end)] = timeslot

    @staticmethod
    def convert_from_espuser(teacher, program, timeslot_dict):
        """Create a AS_Teacher from an ESPUser using a timeslot_dict"""
        assert teacher.isTeacher()
        availability = AS_Timeslot.batch_find(
            teacher.getAvailableTimes(program, ignore_classes=False),
            timeslot_dict)
        is_admin = teacher.isAdministrator()
        return AS_Teacher(availability, teacher.id, is_admin)

    @staticmethod
    def batch_convert(teachers, program, timeslot_dict):
        return map(lambda t: AS_Teacher.convert_from_espuser(
            t, program, timeslot_dict), teachers)


class AS_Classroom:
    def __init__(self, name, available_timeslots,
                 furnishings=None):
        self.name = name
        # Availabilities as roomslots, sorted by the associated timeslot.
        # Does not account for sections the scheduler knows are scheduled.
        self.availability = [AS_RoomSlot(timeslot, self) for timeslot in
                             sorted(available_timeslots)]
        # Dict of resources available in the classroom, mapping from the
        # resource name to AS_Restype.
        self.furnishings = furnishings if furnishings is not None else {}

    @staticmethod
    def convert_from_groupedclassroom(
            classroom, program, timeslot_dict, exclude_availabilities):
        """Create a AS_Classroom from a grouped Classroom (see
        Program.groupedClassrooms()) and Program"""
        assert classroom.res_type == ResourceType.get_or_create("Classroom")
        excluded_availabilities = \
            exclude_availabilities.get(classroom.name, [])
        timeslots = [t for t in classroom.timeslots if
                     t.id not in excluded_availabilities]
        available_timeslots = \
            AS_Timeslot.batch_find(timeslots, timeslot_dict)
        furnishings = AS_ResourceType.batch_convert_resources(
                classroom.furnishings)
        furnishings_dict = {r.name: r for r in furnishings}
        return AS_Classroom(classroom.name, available_timeslots,
                            furnishings_dict)

    def get_roomslots_by_duration(self, start_roomslot, duration):
        """Given a starting roomslot, returns a list of roomslots that
        will cover the length of time specified by duration. If unable
        to do so, return as many roomslots as possible."""
        list_of_roomslots = [start_roomslot]
        classroom_availability = start_roomslot.room.availability
        if start_roomslot not in classroom_availability:
            return []
        index_of_roomslot = classroom_availability.index(start_roomslot)
        start_time = start_roomslot.timeslot.start
        end_time = start_roomslot.timeslot.end
        while duration - (end_time - start_time).seconds/3600.0 \
                > constants.DELTA_TIME:
            index_of_roomslot += 1
            if index_of_roomslot >= len(classroom_availability):
                break
            current_roomslot = classroom_availability[index_of_roomslot]
            list_of_roomslots.append(current_roomslot)
            end_time = current_roomslot.timeslot.end
        return list_of_roomslots

    @staticmethod
    def batch_convert(
            classrooms, program, timeslot_dict, exclude_availabilities):
        return map(lambda c: AS_Classroom.convert_from_groupedclassroom(
            c, program, timeslot_dict, exclude_availabilities), classrooms)


# Ordered by start time, then by end time.
@total_ordering
class AS_Timeslot:
    """A timeslot, not specific to any teacher or class or room."""
    def __init__(self, start, end, event_id=4, associated_roomslots=None):
        self.id = event_id
        self.start = start
        self.end = end
        # AS_RoomSlots during this timeslot
        self.associated_roomslots = associated_roomslots \
            if associated_roomslots is not None else set()

    @staticmethod
    def convert_from_event(event, program):
        """Create an AS_Timeslot from an Event."""
        assert event.parent_program() == program, \
            "Event parent program doesn't match"
        assert event.start < event.end, "Timeslot doesn't end after start time"
        return AS_Timeslot(event.start, event.end, event.id, None)

    def __eq__(self, other):
        if type(other) is type(self):
            return (self.start == other.start) and (self.end == other.end)
        else:
            return False

    def __lt__(self, other):
        return (self.start, self.end) < (other.start, other.end)

    @staticmethod
    def overlaps(timeslot1, timeslot2):
        return (timeslot1.start < timeslot2.end) \
                and (timeslot2.start < timeslot1.end)

    @staticmethod
    def batch_convert(events, program):
        return map(lambda e: AS_Timeslot.convert_from_event(
            e, program), events)

    @staticmethod
    def batch_find(events, timeslot_dict):
        """Finds the timeslots in the dict matching the events. Ignores if it
        doesn't exit."""
        timeslots = []
        for event in events:
            times = (event.start, event.end)
            if times in timeslot_dict:
                timeslot = timeslot_dict[times]
                assert timeslot.id == event.id, \
                    "Timeslot and event ID didn't match"
                timeslots.append(timeslot)
        return sorted(timeslots)


class AS_RoomSlot:
    """A specific timeslot where a specific room is available."""
    def __init__(self, timeslot, room):
        self.timeslot = timeslot
        timeslot.associated_roomslots.add(self)
        self.room = room
        self.assigned_section = None

    @staticmethod
    def batch_convert(events, room, timeslot_dict):
        return map(lambda e: AS_RoomSlot(
            timeslot_dict[(e.start, e.end)], room), events)


class AS_ResourceType:
    def __init__(self, name, restype_id=5, value=""):
        self.id = restype_id
        self.name = name
        self.value = value  # Not in use yet

    @staticmethod
    def convert_from_restype(restype, value=""):
        """Create an AS_ResourceType from a ResourceType"""
        return AS_ResourceType(restype.name, restype.id, value)

    @staticmethod
    def batch_convert_resource_requests(res):
        """Converts from ResourceRequests."""
        return map(
            lambda r: AS_ResourceType.convert_from_restype(
                r.res_type, r.desired_value), res)

    @staticmethod
    def batch_convert_resources(res):
        """Converts from Resources."""
        return map(
            lambda r: AS_ResourceType.convert_from_restype(
                r.res_type, r.attribute_value), res)
