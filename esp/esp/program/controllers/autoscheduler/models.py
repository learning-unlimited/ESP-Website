from django.db.models import Count

from esp.resources.models import ResourceType
from esp.program.models import ClassSection


class AS_Schedule:
    def __init__(self, program, exclude_lunch=True, exclude_walkins=True):
        self.program = program

        # Dict of teachers by id
        self.teachers = {}
        # List of class sections
        self.class_sections = \
            self.load_sections_and_teachers(exclude_lunch, exclude_walkins)

        # List of classrooms
        self.classrooms = map(
                lambda c: AS_Classroom(c, self.program),
                program.groupedClassrooms())

    def load_sections_and_teachers(
            self, exclude_lunch=True, exclude_walkins=True):
        """Loads the program's approved and unscheduled sections from db, and
        registers all teachers into the dict of teachers"""
        ClassSection.objects.annotate(num_meeting_times=Count('meeting_times'))

        # Get all the approved class sections for the program
        sections = ClassSection.objects.filter(
                parent_class__parent_program=self.program,
                status=10)

        # Exclude all already-scheduled classes
        sections = sections.annotate(num_meeting_times=Count("meeting_times"))
        sections = sections.filter(num_meeting_times=0)

        if exclude_lunch:
            sections = sections.exclude(
                    parent_class__category__category="Lunch")
        if exclude_walkins:
            sections = sections.exclude(
                    parent_class__category=self.program.open_class_category)

        # Return!
        return map(lambda s: AS_ClassSection(
            s, self.program, self.teachers), sections)


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
        self.resource_requests = section.getResourceRequests()
        self.viable_times = section.viable_times()


class AS_Teacher:
    def __init__(self, teacher, program):
        """Create a AS_Teacher from an ESPUser"""
        assert teacher.isTeacher()
        self.id = teacher.id
        self.availability = teacher.getAvailableTimes(program)
        self.is_admin = teacher.isAdministrator()


class AS_Classroom:
    def __init__(self, classroom, program):
        """Create a AS_Classroom from a grouped Classroom (see
        Program.groupedClassrooms()) and Program"""
        assert classroom.res_type == ResourceType.get_or_create("Classroom")
        self.id = classroom.id
        self.room = classroom.name
        self.availability = classroom.timeslots  # TODO: verify non-duplicity
        self.furnishings = classroom.furnishings
