from functools import total_ordering
from datetime import timedelta

from django.db.models import Count

from esp.resources.models import ResourceType
from esp.program.models import ClassSection
from esp.users.models import ESPUser


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
        self.classrooms = AS_Classroom.batch_convert(
                program.groupedClassrooms(), self.program, self.timeslot_dict)

    def load_sections_and_teachers(
            self, exclude_lunch, exclude_walkins, exclude_scheduled):
        """Loads the program's approved and unscheduled sections from db, and
        registers all teachers into the dict of teachers"""
        ClassSection.objects.annotate(num_meeting_times=Count('meeting_times'))

        # Get all the approved class sections for the program
        sections = ClassSection.objects.filter(
                parent_class__parent_program=self.program,
                status=10)

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
        return AS_ClassSection.batch_convert(
                sections, self.program, teachers, self.timeslot_dict), \
            teachers


class AS_ClassSection:
    def __init__(self, section, program, teachers_dict, timeslot_dict):
        """Create a AS_ClassSection from a ClassSection and Program"""
        assert section.parent_class.parent_program == program
        self.id = section.id
        self.duration = section.duration
        self.teachers = []
        for teacher in section.teachers:
            if teacher.id not in teachers_dict:
                teachers_dict[teacher.id] = AS_Teacher(
                        teacher, program, timeslot_dict)
            self.teachers.append(teachers_dict[teacher.id])
        self.capacity = section.capacity
        self.resource_requests = AS_ResourceType.batch_convert(
                section.getResourceRequests())
        assert len(section.meeting_times.all()) == 0, "Already-scheduled sections \
            aren't supported yet"
        self.assigned_event = None
        # self.viable_times = \
        #     AS_Timeslot.batch_convert(section.viable_times(), program)

    @staticmethod
    def batch_convert(sections, program, teachers_dict, timeslot_dict):
        return map(lambda s: AS_ClassSection(
            s, program, teachers_dict, timeslot_dict), sections)


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
        self.availability = \
            AS_Event.batch_convert(classroom.timeslots, self, timeslot_dict)
        self.furnishings = AS_ResourceType.batch_convert(classroom.furnishings)

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
        self.start = event.start
        self.end = event.end
        assert self.start < self.end, "Timeslot doesn't end after start time"
        self.associated_events = []  # AS_Events during this timeslot

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
        return [timeslot_dict[(e.start, e.end)] for e in events
                if (e.start, e.end) in timeslot_dict]


class AS_Event:
    """A specific timeslot where a specific room is available."""
    def __init__(self, timeslot, room):
        self.timeslot = timeslot
        timeslot.associated_events.append(self)
        self.room = room
        self.assigned_section = None

    @staticmethod
    def batch_convert(events, room, timeslot_dict):
        return map(lambda e: AS_Event(
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
