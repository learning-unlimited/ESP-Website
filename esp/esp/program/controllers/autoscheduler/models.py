
"""Models for the autoscheduler. Mostly reflects the database on the rest of
the website, but having separate models should be a bit more robust to changes
in website structure and should also be more performant.
"""

from functools import total_ordering
from datetime import timedelta
import hashlib
import json

from django.db.models import Count
from django.db import transaction

from esp.program.controllers.autoscheduler.consistency_checks import \
        ConsistencyChecker
from esp.program.controllers.autoscheduler.exceptions import \
        ConsistencyError, SchedulingError
from esp.resources.models import ResourceType, Resource
from esp.program.models import ClassSection
from esp.users.models import ESPUser
from esp.cal.models import Event
import esp.program.controllers.autoscheduler.constants as constants


class AS_Schedule:
    def __init__(self, program, exclude_lunch=True, exclude_walkins=True,
                 exclude_scheduled=True):
        ESPUser.create_membership_methods()

        self.program = program

        self.timeslots = \
            sorted(AS_Timeslot.batch_convert(program.getTimeSlots(), program))

        # Maps from start and end times to a timeslot.
        self.timeslot_dict = {(t.start, t.end): t for t in self.timeslots}

        # List of class sections and dict of teachers by id
        self.class_sections, self.teachers = \
            self.load_sections_and_teachers(exclude_lunch, exclude_walkins,
                                            exclude_scheduled)

        # List of classrooms
        self.classrooms = set(AS_Classroom.batch_convert(
                program.groupedClassrooms(), self.program, self.timeslot_dict))

    def load_sections_and_teachers(
            self, exclude_lunch, exclude_walkins, exclude_scheduled):
        """Loads the program's approved and unscheduled sections from db, and
        registers all teachers into the dict of teachers"""
        # Get all the approved class sections for the program
        sections = ClassSection.objects.filter(
                parent_class__parent_program=self.program,
                status=10).select_related()

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
        teachers = {}

        # Return!
        return set(AS_ClassSection.batch_convert(
                sections, self.program, teachers, self.timeslot_dict)), \
            teachers

    def save(self, check_consistency=True):
        """Saves the schedule."""
        # TODO: run a constraint check first
        if check_consistency:
            # Run a consistency check first.
            try:
                ConsistencyChecker().run_all_consistency_checks(self)
            except ConsistencyError:
                raise  # TODO

        # Find all sections which we've actually moved.
        changed_sections = set(
            [section for section in self.class_sections
             if section.initial_state
             != section.scheduling_hash()])
        # These are all the sections we are okay changing.
        sections_by_id = {section.id: section for section in
                          self.class_sections}
        unscheduled_sections = set()  # Sections we unscheduled temporarily
        with transaction.atomic():
            for section in changed_sections:
                section_obj = ClassSection.objects.get(id=section.id)
                print "Saving {}".format(section_obj.emailcode())
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
                                sections_by_id,
                                unscheduled_sections,
                                err_msg)

                # Compute our meeting times and classroom
                meeting_times = Event.objects.filter(
                        id__in=[roomslot.timeslot.id
                                for roomslot in section.assigned_roomslots])
                initial_room_num = section.assigned_roomslots[0].room.room
                assert all([roomslot.room.room == initial_room_num
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
                                    sections_by_id,
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

    @staticmethod
    def try_unschedule_section(section, sections_by_id, unscheduled_sections,
                               error_message):
        """Tries to unschedule the given ClassSection. If it's not in the list
        of known sections (sections_by_id), throw a SchedulingError with the
        given error message. Otherwise, make sure the section wasn't moved by
        external sources, and unschedule it."""
        if section.id not in sections_by_id:
            raise SchedulingError(error_message)
        else:
            AS_Schedule.ensure_section_not_moved(section,
                                                 sections_by_id[section.id])
            AS_Schedule.unschedule_section(section, unscheduled_sections)

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
    def __init__(self, section, program, teachers_dict, timeslot_dict):
        """Create a AS_ClassSection from a ClassSection and Program"""
        assert section.parent_class.parent_program == program
        self.id = section.id
        self.initial_state = self.scheduling_hash_of(section)
        self.duration = float(section.duration)
        self.teachers = []
        for teacher in section.teachers:
            if teacher.id not in teachers_dict:
                teachers_dict[teacher.id] = AS_Teacher(
                        teacher, program, timeslot_dict)
            self.teachers.append(teachers_dict[teacher.id])
        self.capacity = section.capacity
        self.resource_requests = set(AS_ResourceType.batch_convert(
                section.getResourceRequests()))
        assert len(section.meeting_times.all()) == 0, "Already-scheduled sections \
            aren't supported yet"
        self.assigned_roomslots = []  # This will be sorted
        assert self.scheduling_hash() == self.initial_state, \
            "AS_ClassSection state doesn't match ClassSection state"

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
        rooms = sorted(list(set([r.room.room for r in
                                self.assigned_roomslots])))
        state_str = json.dumps([meeting_times, rooms])
        return hashlib.md5(state_str).hexdigest()

    @staticmethod
    def batch_convert(sections, program, teachers_dict, timeslot_dict):
        return map(lambda s: AS_ClassSection(
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
    def __init__(self, teacher, program, timeslot_dict):
        """Create a AS_Teacher from an ESPUser"""
        assert teacher.isTeacher()
        self.id = teacher.id
        self.availability = AS_Timeslot.batch_find(
            teacher.getAvailableTimes(program, ignore_classes=False),
            timeslot_dict)
        self.is_admin = teacher.isAdministrator()

    @staticmethod
    def batch_convert(teachers, program, timeslot_dict):
        return map(lambda t: AS_Teacher(t, program, timeslot_dict), teachers)


class AS_Classroom:
    def __init__(self, classroom, program, timeslot_dict):
        """Create a AS_Classroom from a grouped Classroom (see
        Program.groupedClassrooms()) and Program"""
        assert classroom.res_type == ResourceType.get_or_create("Classroom")
        self.id = classroom.id
        self.room = classroom.name
        # Availabilities as roomslots, sorted by the associated timeslot.
        # Does not account for sections the scheduler knows are scheduled.
        self.availability = sorted(
            AS_RoomSlot.batch_convert(
                classroom.timeslots, self, timeslot_dict),
            key=lambda r: r.timeslot)
        self.furnishings = set(
            AS_ResourceType.batch_convert(classroom.furnishings))

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
        while abs((end_time - start_time).seconds/3600.0 - duration) \
                > constants.DELTA_TIME:
            index_of_roomslot += 1
            if index_of_roomslot >= len(classroom_availability):
                break
            current_roomslot = classroom_availability[index_of_roomslot]
            list_of_roomslots.append(current_roomslot)
            end_time = current_roomslot.timeslot.end
        return list_of_roomslots

    @staticmethod
    def batch_convert(classrooms, program, timeslot_dict):
        return map(lambda c: AS_Classroom(
            c, program, timeslot_dict), classrooms)


# Ordered by start time, then by end time.
@total_ordering
class AS_Timeslot:
    """A timeslot, not specific to any teacher or class or room."""
    def __init__(self, event, program):
        """Create an AS_Timeslot from an Event."""
        assert event.parent_program() == program, \
            "Event parent program doesn't match"
        self.id = event.id
        self.start = event.start
        self.end = event.end
        assert self.start < self.end, "Timeslot doesn't end after start time"
        self.associated_roomslots = set()  # AS_RoomSlots during this timeslot

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
    def contiguous(timeslot1, timeslot2):
        """ Returns true if the second argument is less than 20 minutes apart
        from the first one.

        Duplicates logic from esp.cal.Event.
        """
        tol = timedelta(minutes=20)

        if (timeslot2.start - timeslot2.end) < tol:
            return True
        else:
            return False

    @staticmethod
    def batch_convert(events, program):
        return map(lambda e: AS_Timeslot(e, program), events)

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
    def __init__(self, restype):
        """Create an AS_ResourceType from a ResourceType"""
        self.id = restype.id
        self.name = restype.name
        self.description = restype.description

    @staticmethod
    def batch_convert(res):
        """Converts from ResourceRequests or Resources."""
        return map(lambda r: AS_ResourceType(r.res_type), res)
