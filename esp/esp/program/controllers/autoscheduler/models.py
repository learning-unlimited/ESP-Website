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

        # List of class sections and dict of teachers by id
        self.class_sections, self.teachers = \
            self.load_sections_and_teachers(exclude_lunch, exclude_walkins,
                                            exclude_scheduled)

        # List of classrooms
        self.classrooms = map(
                lambda c: AS_Classroom(c, self.program),
                program.groupedClassrooms())

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
        return map(lambda s: AS_ClassSection(
            s, self.program, teachers), sections), teachers


class AS_ClassSection:
    def __init__(self, section, program, teachers_dict):
        """Create a AS_ClassSection from a ClassSection and Program"""
        assert section.parent_class.parent_program == program
        self.id = section.id
        self.duration = section.duration
        self.teachers = []
        for teacher in section.teachers:
            if teacher.id not in teachers_dict:
                teachers_dict[teacher.id] = AS_Teacher(teacher, program)
            self.teachers.append(teachers_dict[teacher.id])
        self.capacity = section.capacity
        self.resource_requests = \
            map(lambda r: AS_ResourceType(r.res_type),
                section.getResourceRequests())
        self.viable_times = map(lambda e: AS_Timeblock(e, program),
                                section.viable_times())


class AS_Teacher:
    def __init__(self, teacher, program):
        """Create a AS_Teacher from an ESPUser"""
        assert teacher.isTeacher()
        self.id = teacher.id
        self.availability = map(lambda e: AS_Timeblock(e, program),
                                teacher.getAvailableTimes(program))
        self.is_admin = teacher.isAdministrator()


class AS_Classroom:
    def __init__(self, classroom, program):
        """Create a AS_Classroom from a grouped Classroom (see
        Program.groupedClassrooms()) and Program"""
        assert classroom.res_type == ResourceType.get_or_create("Classroom")
        self.id = classroom.id
        self.room = classroom.name
        self.availability = map(lambda e: AS_Timeblock(e, program),
                                classroom.timeslots)
        self.furnishings = map(lambda r: AS_ResourceType(r.res_type),
                               classroom.furnishings)


# Ordered by start time, then by end time.
@total_ordering
class AS_Timeblock:
    def __init__(self, event, program):
        """Create an AS_Timeblock from an Event."""
        assert event.parent_program() == program, \
            "Event parent program doesn't match"
        self.start = event.start
        self.end = event.end
        assert self.start < self.end, "Timeblock doesn't end after start time"

    def __eq__(self, other):
        if type(other) is type(self):
            return (self.start == other.start) and (self.end == other.end)
        else:
            return False

    def __lt__(self, other):
        return (self.start, self.end) < (other.start, other.end)

    @staticmethod
    def overlaps(block1, block2):
        return (block1.start < block2.end) and (block2.start < block1.end)

    @staticmethod
    def contiguous(block1, block2):
        """ Returns true if the second argument is less than 20 minutes apart
        from the first one.

        Duplicates logic from esp.cal.Event.
        """
        tol = timedelta(minutes=20)

        if (block2.start - block2.end) < tol:
            return True
        else:
            return False


class AS_ResourceType:
    def __init__(self, restype):
        """Create an AS_ResourceType from a ResourceType"""
        self.id = restype.id
        self.name = restype.name
        self.description = restype.description
