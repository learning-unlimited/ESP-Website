from esp.resources.models import ResourceType


class AS_ClassSection:
    def __init__(self, section, program):
        """Create a AS_ClassSection from a ClassSection and Program"""
        assert section.parent_class.parent_program == program
        # TODO: check types to make sure they're int, float, etc.
        self.id = section.id
        self.duration = section.duration
        self.teachers = section.teachers
        self.capacity = section.capacity
        self.resource_requests = section.getResourceRequests()


class AS_Teacher:
    def __init__(self, teacher, program):
        """Create a AS_Teacher from an ESPUser"""
        assert teacher.isTeacher()
        self.id = teacher.id
        self.availability = teacher.getAvailableTimes(program)
        self.is_admin = teacher.isAdministrator()


class AS_Classroom:
    def __init__(self, classroom, program):
        """Create a AS_Classroom from a Resource and Program"""
        assert classroom.res_type == ResourceType.get_or_create("Classroom")
        self.id = classroom.id
        self.room = classroom.name
        self.availability = classroom.available_times(program)
