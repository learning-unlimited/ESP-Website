
"""Models for the autoscheduler. Mostly reflects the database on the rest of
the website, but having separate models should be a bit more robust to changes
in website structure and should also be more performant.
"""

from functools import total_ordering
import hashlib
import json
import bisect

from django.db.models import Count
from django.db import transaction

from esp.program.controllers.autoscheduler.consistency_checks import \
        ConsistencyChecker
from esp.program.controllers.autoscheduler.exceptions import \
        ConsistencyError, SchedulingError
import esp.program.controllers.autoscheduler.constants as constants
from esp.program.controllers.autoscheduler.constraints import \
        CompositeConstraint
from esp.program.controllers.autoscheduler import util
from esp.resources.models import \
    ResourceType, Resource, ResourceAssignment, ResourceRequest
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

        schedule.run_consistency_checks()
        schedule.run_constraint_checks()

        return schedule

    def load_sections_and_teachers_and_classrooms(
            self, require_approved, exclude_lunch,
            exclude_walkins, exclude_scheduled):
        """Loads the program's approved and unscheduled sections from db, and
        registers all teachers into the dict of teachers"""
        print "Loading"

        # Get all the approved class sections for the program
        sections = ClassSection.objects.filter(
                parent_class__parent_program=self.program,
                ).select_related()

        if require_approved:
            sections = sections.filter(status=10)
        if exclude_scheduled:
            # Exclude all already-scheduled classes
            sections = sections.annotate(
                    num_meeting_times=Count("meeting_times"))
            sections = sections.filter(num_meeting_times=0)

        if exclude_lunch:
            sections = sections.exclude(
                    parent_class__category__category="Lunch")
        if exclude_walkins:
            sections = sections.exclude(
                    parent_class__category=self.program.open_class_category)

        print "Filtered"

        # For all excluded sections, remove their availabilities

        teachers = {}

        known_sections = {section.id: section for section in sections}
        rooms_by_section, meeting_times_by_section, requests_by_section = \
            AS_ClassSection.load_section_assignments(known_sections)
        print "Assignments loaded"
        # Load classrooms from groupedClassrooms
        classrooms = AS_Classroom.convert_from_resources(
                self.program.getClassrooms(), self.program,
                self.timeslot_dict, known_sections,
                rooms_by_section, meeting_times_by_section)
        print "Classrooms loaded"

        converted_sections = AS_ClassSection.batch_convert(
            sections, self.program, teachers, self.timeslot_dict, classrooms,
            rooms_by_section, meeting_times_by_section,
            requests_by_section)
        print "Sections converted"

        sections_dict = {sec.id: sec for sec in converted_sections}
        print "Sections dict loaded"

        # Return!
        return sections_dict, teachers, classrooms

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
                if section.is_scheduled():
                    start_time = section.assigned_roomslots[0].timeslot.start
                    end_time = section.assigned_roomslots[-1].timeslot.end
                    # Make sure the teacher is available
                    for teacher in section.teachers:
                        teacher_obj = ESPUser.objects.get(id=teacher.id)
                        other_sections = \
                            teacher_obj.getTaughtSections(self.program)
                        for other_section in other_sections:
                            conflict = False
                            for other_time in \
                                    other_section.get_meeting_times():
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
                                    for roomslot
                                    in section.assigned_roomslots])
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
                else:
                    section_obj.clearRooms()
                    section_obj.clear_meeting_times()

                # Update the section's initial_state so we don't confuse
                # ourselves
                section.recompute_hash()

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
        violation = self.constraints.check_schedule(self)
        if violation is not None:
            raise SchedulingError(("Schedule violated constraints: {}"
                                  .format(violation)))

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
        for roomslot in assigned_roomslots:
            roomslot.assigned_section = self
            for teacher in self.teachers:
                teacher.add_availability(roomslot.timeslot)
        # Dict from restype names to AS_Restypes requested
        self.resource_requests = resource_requests \
            if resource_requests is not None else {}

        # A hash of the initial state.
        self.recompute_hash()
        self.register_teachers()

    @staticmethod
    def convert_from_classection_obj(
            section, program, teachers_dict, timeslot_dict, rooms,
            rooms_by_section, meeting_times_by_section,
            requests_by_section):
        """Create a AS_ClassSection from a ClassSection and Program. Will also
        populate the given dictionary of teachers and uses the given dictionary
        of timeslots for availabilities. """
        if not AS_ClassSection.section_satisfies_constraints(
                section, rooms_by_section, meeting_times_by_section):
            print ("Warning: Autoscheduler can't handle section {}"
                   .format(section.emailcode()))
            return None

        teachers = []
        for teacher in section.teachers:
            if teacher.id not in teachers_dict:
                teachers_dict[teacher.id] = AS_Teacher.convert_from_espuser(
                        teacher, program, timeslot_dict)
            teachers.append(teachers_dict[teacher.id])

        resource_requests = AS_ResourceType.batch_convert_resource_requests(
                requests_by_section[section.id])

        resource_requests_dict = {r.name: r for r in resource_requests}
        roomslots = []
        for classroom in rooms_by_section[section.id]:
            room = rooms[classroom.name]
            event = classroom.event
            roomslots.append(room.availability_dict[(event.start, event.end)])
        roomslots.sort(key=lambda r: r.timeslot)

        as_section = AS_ClassSection(
                teachers, float(section.duration), section.capacity,
                section.category.id, roomslots,
                section_id=section.id,
                grade_min=section.parent_class.grade_min,
                grade_max=section.parent_class.grade_max,
                resource_requests=resource_requests_dict)

        assert as_section.scheduling_hash_of(
                section, rooms_by_section, meeting_times_by_section) == \
            as_section.initial_state, \
            ("AS_ClassSection state doesn't match ClassSection state "
             "for section {}".format(section.emailcode()))

        return as_section

    @staticmethod
    def load_section_assignments(section_ids):
        """Returns a dict mapping from section id to Classroom resources, and
        from section id to lists of meeting times, and from section id to
        resource requests. The purpose of using this is
        to minimize database queries."""
        resource_assignments = ResourceAssignment.objects.filter(
            target__in=section_ids, resource__res_type__name="Classroom"
            ).values_list("target", "resource")
        sections_by_resource = {resource: target for target, resource in
                                resource_assignments}
        resources = Resource.objects.filter(
            id__in=sections_by_resource
        ).select_related()
        rooms_by_section = {section: [] for section in section_ids}
        for resource in resources:
            rooms_by_section[
                sections_by_resource[resource.id]].append(resource)
        meeting_times = ClassSection.objects.filter(
            id__in=section_ids
        ).values_list("id", "meeting_times")
        all_meeting_times = set([time for sec, time in meeting_times if time is
                                not None])
        meeting_time_objs = Event.objects.filter(
            id__in=all_meeting_times
        ).select_related()
        meeting_times_by_id = {e.id: e for e in meeting_time_objs}
        meeting_times_by_section = {section: [] for section in section_ids}
        for section, time in meeting_times:
            if time is not None:
                meeting_times_by_section[section].append(
                    meeting_times_by_id[time])

        requests = ResourceRequest.objects.filter(
            target__in=section_ids).select_related("target", "res_type")
        requests_by_section = {section: [] for section in section_ids}
        for request in requests:
            requests_by_section[request.target.id].append(request)
        return rooms_by_section, meeting_times_by_section, \
            requests_by_section

    @staticmethod
    def section_satisfies_constraints(
            section_obj, rooms_by_section, meeting_times_by_section):
        """Returns False if the section:
         - Is scheduled in more than one classroom
         - Meeting times disagree with classroomassignments
         - Is scheduled in nonconsecutive timeslots
         - Isn't scheduled for its duration"""
        classrooms = sorted(
            rooms_by_section[section_obj.id], key=lambda c: c.event)
        meeting_times = sorted(meeting_times_by_section[section_obj.id])
        if len(classrooms) != len(meeting_times):
            return False
        for room1, time1, room2, time2 in zip(
                classrooms, meeting_times, classrooms[1:], meeting_times[1:]):
            # This function was written for AS_Timeslots, but it also works
            # with Events.
            if not util.contiguous(time1, time2):
                return False  # Not contiguous
            if room1.event != time1 or room2.event != time2:
                return False  # Not the same time
            if room1.name != room2.name:
                return False  # Different rooms
        if len(meeting_times) > 0:
            start_time = meeting_times[0].start
            end_time = meeting_times[-1].end
            scheduled_duration = (end_time - start_time).seconds / 3600.0
            if abs(scheduled_duration - float(section_obj.duration)) \
                    > constants.DELTA_TIME:
                return False
        return True

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

    def recompute_hash(self):
        self.initial_state = self.scheduling_hash()

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
    def batch_convert(sections, program, teachers_dict, timeslot_dict, rooms,
                      rooms_by_section, meeting_times_by_section,
                      requests_by_section):
        return [s for s in
                map(lambda s: AS_ClassSection.convert_from_classection_obj(
                    s, program, teachers_dict, timeslot_dict, rooms,
                    rooms_by_section, meeting_times_by_section,
                    requests_by_section), sections)
                if s is not None]

    @staticmethod
    def scheduling_hash_of(
            section, rooms_by_section=None, meeting_times_by_section=None):
        """Creates a unique hash based on the timeslots and rooms assigned to a
        section."""
        meeting_times = meeting_times_by_section[section.id] \
            if meeting_times_by_section is not None \
            else section.get_meeting_times()
        meeting_times = sorted([(str(e.start), str(e.end))
                                for e in meeting_times])
        rooms = rooms_by_section[section.id] if rooms_by_section is not None \
            else section.classrooms()
        rooms = sorted(list(set([r.name for r in rooms])))
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

    def add_availability(self, timeslot):
        if (timeslot.start, timeslot.end) not in self.availability_dict:
            bisect.insort_left(self.availability, timeslot)
            self.availability_dict[(timeslot.start, timeslot.end)] = timeslot

    @staticmethod
    def convert_from_espuser(teacher, program, timeslot_dict):
        """Create a AS_Teacher from an ESPUser using a timeslot_dict"""
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
        self.availability_dict = {(r.timeslot.start, r.timeslot.end): r
                                  for r in self.availability}

    @staticmethod
    def convert_from_resources(classrooms, program, timeslot_dict,
                               known_sections,
                               rooms_by_section, meeting_times_by_section):
        """Create a dict by roon name of AS_Classroms from a collection of
        Resources. Also takes in a dict of known sections mapping from ids to
        ClassSection objects, and two dicts from section ids to lists of
        Classroom Resource objects (i.e. the classrooms themselves) and to
        their meeting times. If a resource is unavailable, then either schedule
        the offending class in it (if we know about said section) or don't mark
        it as an availability."""

        # Dict mapping from names to timeslots and furnishings.
        classroom_info_dict = {}
        # Build a dict mapping from resources and events to lists of targets
        all_assignments = (
            ResourceAssignment.objects.filter(resource__in=classrooms)
            .values_list(
                "resource__name", "resource__event__id", "target__id"))
        resource_groups = [r.res_group_id for r in classrooms
                           if r.res_group_id is not None]
        all_furnishings = Resource.objects.filter(
            res_group__in=resource_groups).exclude(
            res_type__name="Classroom").select_related()
        furnishings_by_group = {group_id: [] for group_id in resource_groups}
        for furnishing in all_furnishings:
            furnishings_by_group[furnishing.res_group_id].append(furnishing)
        assignments_dict = {}
        for resource, event, target in all_assignments:
            if resource not in assignments_dict:
                assignments_dict[(resource, event)] = []
            assignments_dict[
                (resource, event)].append(target)
        for classroom in classrooms:
            assert classroom.res_type == \
                ResourceType.get_or_create("Classroom")
            assignments = assignments_dict.get(
                (classroom.name, classroom.event.id), [])
            unavailable = False
            if len(assignments) > 1:
                # If a room is double-booked, we can ignore it if it doesn't
                # contain any sections we care about. Otherwise, give up.
                unavailable = True
                for target in assignments:
                    if target in known_sections:
                        raise SchedulingError(
                            "Room {} is double-booked and has known section " +
                            "num {}".format(classroom.name, target))
            elif len(assignments) == 1:
                target = assignments[0]
                if target not in known_sections:
                    unavailable = True
                elif not AS_ClassSection.section_satisfies_constraints(
                        known_sections[target],
                        rooms_by_section, meeting_times_by_section):
                    unavailable = True
            if not unavailable:
                if classroom.name not in classroom_info_dict:
                    furnishing_objs = \
                        furnishings_by_group[classroom.res_group_id] \
                        if classroom.res_group_id is not None else []
                    furnishings = AS_ResourceType.batch_convert_resources(
                        furnishing_objs)
                    furnishings_dict = {r.name: r for r in furnishings}
                    classroom_info_dict[classroom.name] = \
                        ([], furnishings_dict)
                event = classroom.event
                timeslot = timeslot_dict[(event.start, event.end)]
                classroom_info_dict[classroom.name][0].append(timeslot)
        classroom_dict = {}
        for room in classroom_info_dict:
            timeslots, furnishings = classroom_info_dict[room]
            classroom_dict[room] = AS_Classroom(room, timeslots, furnishings)
        return classroom_dict

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
