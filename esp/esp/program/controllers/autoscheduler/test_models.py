import datetime

from esp.cal.models import Event
from esp.program.models.class_ import ClassSubject
from esp.resources.models import Resource, ResourceType, ResourceRequest
from esp.program.tests import ProgramFrameworkTest


class ScheduleTest(ProgramFrameworkTest):
    def setUp(self):
        # Explicit settings, but we'll also add a new timeslot, room and class.
        # The new class and room will request and have a new resource,
        # respectively.
        # This increases the complexity of the program for stricter testing.
        settings = {
            'num_timeslots': 6,
            'timeslot_length': 50,
            'timeslot_gap': 10,
            'room_capacity': 30,
            'num_categories': 2,
            'num_rooms': 4,
            'num_teachers': 5,
            'classes_per_teacher': 2,
            'sections_per_class': 1,
            'num_students': 0,
            'num_admins': 1,
            'program_type': 'TestProgram',
            'program_instance_name': '2222_Summer',
            'program_instance_label': 'Summer 2222',
            'start_time': datetime.datetime(2222, 7, 7, 7, 5),
        }
        extra_settings = {
            "extra_timeslot_start": datetime.datetime(2222, 7, 8, 7, 5),
            "extra_room_capacity": 151,
            "extra_room_availability": [1, 2, 4, 5],  # Timeslot indices
            "extra_class_teachers": [0, 3],  # Teacher indices
            "extra_class_sections": 2,
            "extra_class_category": 0,  # Category index
            "extra_class_size": 200,
            "extra_class_grade_min": 9,
            "extra_class_grade_max": 10,
            "extra_class_duration": 2,  # Number of timeslots
            "teacher_admin_idx": 0,  # This teacher is also an admin
            "extra_resource_type_name": "Projector",
            "extra_resource_value": "Foo",
        }
        self.setUpProgram(settings, extra_settings)
        self.setUpSchedule(settings, extra_settings)

    def setUpProgram(self, settings, extra_settings):
        # Initialize the program.
        super(ScheduleTest, self).setUp(**settings)
        # Create an extra timeslot.
        start_time = extra_settings["extra_timeslot_start"]
        end_time = start_time + datetime.timedelta(
                minutes=settings["timeslot_length"])
        Event.objects.get_or_create(
                program=self.program,
                event_type=self.event_type,
                start=start_time,
                end=end_time,
                short_description="Extra Slot",
                description=start_time.strftime("%H:%M %m/%d/%Y")
        )
        self.timeslots = self.program.getTimeSlots()

        # Create an extra room with the new resource
        res_type = ResourceType.get_or_creat(
                extra_settings["extra_resource_type_name"])
        for i in extra_settings["extra_room_availability"]:
            room_capacity = extra_settings["extra_room_capacity"]
            room, created = Resource.objects.get_or_create(
                name="Extra Room",
                num_students=room_capacity,
                event=self.timeslots[i],
                res_type=ResourceType.get_or_create("Classroom"))
            Resource.objects.get_or_create(
                name="Extra Room Projector",
                event=self.timeslots[i],
                res_type=res_type,
                res_group=room.res_group,
                attribute_value=extra_settings["extra_resource_value"],)
        self.rooms = self.program.getClassrooms()

        # Create an extra class
        duration = (
            (settings["timeslot length"]
                * extra_settings["extra_class_duration"])
            + (settings["timeslot gap"]
                * (extra_settings["extra_class_duration"] - 1))
            ) / 60.0
        new_class, created = ClassSubject.objects.get_or_create(
                title="Extra Class",
                category=self.categories[
                    extra_settings["extra_class_category"]],
                grade_min=extra_settings["extra_class_grade_min"],
                grade_max=extra_settings["extra_class_grade_max"],
                parent_program=self.program,
                class_size_max=extra_settings["extra_class_size"],
                class_info="Extra Desctiption!",
                duration=duration)
        for i in extra_settings["extra_class_teachers"]:
            new_class.add_teacher(self.teachers[i])
        for i in xrange(extra_settings["extra_class_sections"]):
            if new_class.get_sections().count() <= i:
                new_class.add_section(duration=duration)
        new_class.accept()
        # Add resource requests to the new sections.
        for section in new_class.get_sections():
            ResourceRequest.objects.get_or_create(
                target=section,
                target_subj=section.parent_class,
                res_type=res_type,
                desired_value=extra_settings["extra_resource_value"])

        # Set availabilities: each teacher is available except in the timeslot
        # sharing his index (e.g. teacher 0 isn't available in the 0th
        # timeslot)
        for i, t in enumerate(self.teachers):
            for j, ts in self.timeslots:
                if i != j:
                    t.addAvailableTime(self.program, ts)

        self.teachers[
                extra_settings["teacher_admin_idx"]].makeRole("Administrator")

    def setUpSchedule(self, settings, extra_settings):
        # TODO
        pass
