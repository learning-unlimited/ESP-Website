import datetime
import traceback

from django.db.models import Min

from esp.cal.models import Event
import esp.program.controllers.autoscheduler.data_model as data_model
import esp.program.controllers.autoscheduler.db_interface as db_interface
from esp.program.controllers.autoscheduler.exceptions import SchedulingError
import esp.program.controllers.autoscheduler.util as util
from esp.program.models.class_ import \
        ClassSubject, ClassSection, ClassCategories
from esp.program.modules import module_ext
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import Resource, ResourceType, ResourceRequest


class ScheduleLoadAndSaveTest(ProgramFrameworkTest):
    def setUp(self):
        # Explicit settings, but we'll also add a new timeslot, room and class.
        # The new class and room will request and have a new resource,
        # respectively.
        # This increases the complexity of the program for stricter testing.
        self.settings = {
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
        self.extra_settings = {
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
        self.setUpProgram(self.settings, self.extra_settings)
        self.schedule = self.setUpSchedule(self.settings, self.extra_settings)

    def setUpProgram(self, settings, extra_settings):
        # Initialize the program.
        super(ScheduleLoadAndSaveTest, self).setUp(**settings)
        self.initial_timeslot_id = util.get_min_id(self.timeslots)
        self.initial_teacher_id = util.get_min_id(self.teachers)
        self.initial_category_id = util.get_min_id(self.categories)
        self.initial_restype_id = 1 + len(ResourceType.objects.all())
        self.initial_section_id = ClassSection.objects.filter(
                parent_class__parent_program=self.program
        ).aggregate(Min('id'))['id__min']
        self.initial_subject_id = ClassSubject.objects.filter(
                parent_program=self.program).aggregate(Min('id'))['id__min']

        # Create an extra timeslot.
        start_time = extra_settings["extra_timeslot_start"]
        end_time = start_time + datetime.timedelta(
                minutes=settings["timeslot_length"])
        self.extra_timeslot, created = Event.objects.get_or_create(
                program=self.program,
                event_type=self.event_type,
                start=start_time,
                end=end_time,
                short_description="Extra Slot",
                description=start_time.strftime("%H:%M %m/%d/%Y")
        )
        self.timeslots = self.program.getTimeSlots()

        # Create an extra room with the new resource
        res_type = ResourceType.get_or_create(
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
            (settings["timeslot_length"]
                * extra_settings["extra_class_duration"])
            + (settings["timeslot_gap"]
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
            new_class.makeTeacher(self.teachers[i])
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
            for j, ts in enumerate(self.timeslots):
                if i != j:
                    t.addAvailableTime(self.program, ts)

        self.teachers[
                extra_settings["teacher_admin_idx"]].makeRole("Administrator")

    def setUpSchedule(self, settings, extra_settings):
        """Creates the schedule we expect to see for the given settings and
        extra settings, reflecting the combination of the implementation of
        ProgramFrameworkTest.setUp and setUpProgram above. Returns said
        schedule."""
        # Create timeslots
        timeslots = []
        timeslot_id = self.initial_timeslot_id
        for i in xrange(settings["num_timeslots"]):
            start_time = settings["start_time"] \
                + datetime.timedelta(minutes=(
                    i * (settings["timeslot_length"]
                         + settings["timeslot_gap"])))
            end_time = start_time + \
                datetime.timedelta(minutes=settings["timeslot_length"])
            timeslots.append(data_model.AS_Timeslot(
                start_time, end_time, timeslot_id, None))
            timeslot_id += 1
        start_time = extra_settings["extra_timeslot_start"]
        end_time = start_time + datetime.timedelta(
                minutes=settings["timeslot_length"])
        timeslots.append(data_model.AS_Timeslot(
            start_time, end_time, timeslot_id, None))

        # Create classrooms and furnishings
        classrooms = []
        capacity = settings["room_capacity"]
        for i in xrange(settings["num_rooms"]):
            classrooms.append(data_model.AS_Classroom(
                "Room {}".format(str(i)), capacity, timeslots[:-1]))
        restype_id = ResourceType.objects.get(
            name=extra_settings["extra_resource_type_name"]).id
        extra_resource_type = data_model.AS_ResourceType(
            extra_settings["extra_resource_type_name"],
            restype_id,
            extra_settings["extra_resource_value"])
        room_timeslots = [timeslots[i] for i in
                          extra_settings["extra_room_availability"]]
        classrooms.append(data_model.AS_Classroom(
                "Extra Room", extra_settings["extra_room_capacity"],
                room_timeslots,
                {extra_resource_type.name: extra_resource_type}))
        classrooms_dict = {room.name: room for room in classrooms}

        # Create teachers
        teachers = []
        for i in xrange(settings["num_teachers"]):
            teacher_id = i + self.initial_teacher_id
            teacher_availability = [
                    ts for j, ts in enumerate(timeslots) if j != i]
            is_admin = (i == extra_settings["teacher_admin_idx"])
            teachers.append(data_model.AS_Teacher(
                teacher_availability, teacher_id, is_admin))
        teachers_dict = {teacher.id: teacher for teacher in teachers}

        # Create sections
        subject_count = 0
        section_id = self.initial_section_id
        subject_id = self.initial_subject_id
        sections = []
        for t in teachers:
            for i in xrange(settings["classes_per_teacher"]):
                category_id = self.initial_category_id + \
                    (subject_count % settings["num_categories"])
                grade_min = 7
                grade_max = 12
                capacity = settings["room_capacity"]
                subject_count += 1
                duration = settings["timeslot_length"] / 60.0
                for j in xrange(settings["sections_per_class"]):
                    sections.append(data_model.AS_ClassSection(
                        [t], duration, capacity,
                        category_id, [],
                        section_id, subject_id,
                        grade_min=grade_min, grade_max=grade_max))
                    section_id += 1
                subject_id += 1
        category_id = extra_settings["extra_class_category"] \
            + self.initial_category_id
        grade_min = extra_settings["extra_class_grade_min"]
        grade_max = extra_settings["extra_class_grade_max"]
        capacity = extra_settings["extra_class_size"]
        duration = (
            (settings["timeslot_length"]
                * extra_settings["extra_class_duration"])
            + (settings["timeslot_gap"]
                * (extra_settings["extra_class_duration"] - 1))
            ) / 60.0
        section_teachers = [
            t for i, t in enumerate(teachers)
            if i in extra_settings["extra_class_teachers"]]
        resource_requests = {extra_resource_type.name: extra_resource_type}
        self.extra_section_ids = []
        for i in xrange(extra_settings["extra_class_sections"]):
            self.extra_section_ids.append(section_id)
            sections.append(data_model.AS_ClassSection(
                section_teachers, duration, capacity,
                category_id, [],
                section_id, subject_id,
                grade_min=grade_min, grade_max=grade_max,
                resource_requests=resource_requests))
            section_id += 1
        subject_id += 1
        sections_dict = {section.id: section for section in sections}

        return data_model.AS_Schedule(
            program=self.program, timeslots=timeslots,
            class_sections=sections_dict, teachers=teachers_dict,
            classrooms=classrooms_dict)

    def assert_roomslot_equality(self, roomslot1, roomslot2):
        """Performs asserts to check two roomslots are equal."""
        self.assertEqual(roomslot1.timeslot.id, roomslot2.timeslot.id)
        self.assertEqual(roomslot1.room.name, roomslot2.room.name)
        if (roomslot1.assigned_section is None):
            self.assertEqual(roomslot2.assigned_section, None)
        else:
            self.assertEqual(roomslot1.assigned_section.id,
                             roomslot2.assigned_section.id)

    def assert_restype_equality(self, restype1, restype2):
        """Performs asserts to check that two AS_ResTypes are equal."""
        self.assertEqual(restype1.id, restype2.id)
        self.assertEqual(restype1.name, restype2.name)
        self.assertEqual(restype1.value, restype2.value)

    def assert_section_equality(self, section1, section2):
        """Performs asserts to check two sections are equal."""
        self.assertEqual(section1.id, section2.id)
        self.assertEqual(section1.parent_class, section2.parent_class)
        self.assertAlmostEqual(section1.duration, section2.duration, places=2)
        self.assertEqual(
            set(t.id for t in section1.teachers),
            set(t.id for t in section2.teachers))
        self.assertEqual(section1.grade_min, section2.grade_min)
        self.assertEqual(section1.grade_max, section2.grade_max)
        self.assertEqual(section1.category, section2.category)
        self.assertEqual(len(section1.assigned_roomslots),
                         len(section2.assigned_roomslots))
        for rs1, rs2 in \
                zip(section1.assigned_roomslots, section2.assigned_roomslots):
            self.assert_roomslot_equality(rs1, rs2)

        self.assertSetEqual(set(section1.resource_requests.keys()),
                            set(section2.resource_requests.keys()))
        for restype_name in section1.resource_requests:
            self.assert_restype_equality(
                section1.resource_requests[restype_name],
                section2.resource_requests[restype_name])

        self.assertEqual(section1.initial_state, section2.initial_state)

    def assert_teacher_equality(self, teacher1, teacher2):
        """Perform asserts to check that two AS_Teachers are equal."""
        self.assertEqual(teacher1.id, teacher2.id)
        self.assertEqual(teacher1.availability, teacher2.availability)
        self.assertSetEqual(set(teacher1.taught_sections.keys()),
                            set(teacher2.taught_sections.keys()))
        self.assertEqual(teacher1.is_admin, teacher2.is_admin)

    def assert_classroom_equality(self, room1, room2):
        """Perform asserts to check that two AS_Classrooms are equal."""
        self.assertEqual(room1.name, room2.name)
        self.assertEqual(room1.capacity, room2.capacity)
        self.assertEqual(len(room1.availability), len(room2.availability))
        for rs1, rs2 in zip(room1.availability, room2.availability):
            self.assert_roomslot_equality(rs1, rs2)
        self.assertSetEqual(set(room1.furnishings.keys()),
                            set(room2.furnishings.keys()))
        for furnishing_name in room1.furnishings:
            self.assert_restype_equality(
                room1.furnishings[furnishing_name],
                room2.furnishings[furnishing_name])

    def assert_schedule_equality(self, schedule1, schedule2):
        """Perform asserts to check that two schedules are equal."""
        self.assertEqual(schedule1.program, schedule2.program)
        self.assertEqual(schedule1.timeslots, schedule2.timeslots)
        self.assertSetEqual(set(schedule1.class_sections.keys()),
                            set(schedule2.class_sections.keys()))
        for section_id in schedule1.class_sections:
            self.assert_section_equality(
                    schedule1.class_sections[section_id],
                    schedule2.class_sections[section_id])
        self.assertSetEqual(set(schedule1.teachers.keys()),
                            set(schedule2.teachers.keys()))
        for teacher_id in schedule1.teachers:
            self.assert_teacher_equality(
                schedule1.teachers[teacher_id], schedule2.teachers[teacher_id])

        self.assertSetEqual(set(schedule1.classrooms.keys()),
                            set(schedule2.classrooms.keys()))
        for room_name in schedule1.classrooms:
            self.assert_classroom_equality(
                schedule1.classrooms[room_name],
                schedule2.classrooms[room_name])

    def schedule_class_simple_model(self, schedule=None, recompute_hash=False):
        """Schedules section 0 in timeslot 1 of room 1.
        Returns said section and roomslot. This operates on self.schedule, or a
        provided one."""
        if schedule is None:
            schedule = self.schedule
        section = schedule.class_sections[self.initial_section_id]
        room = schedule.classrooms["Room 1"]
        roomslot = room.availability[1]
        section.assign_roomslots([roomslot])
        if recompute_hash:
            section.recompute_hash()
        schedule.run_consistency_checks()
        schedule.run_constraint_checks()
        return section, roomslot

    def remove_class_simple_model(self, schedule=None):
        """Removes section 0, as well as timeslot 1 of room 1. (This corresponds
        to section 0 being scheduled in this roomslot and us not knowing about
        section 0. Also removes the availabilities of the teachers teaching at
        that time."""
        if schedule is None:
            schedule = self.schedule
        section = schedule.class_sections[self.initial_section_id]
        room = schedule.classrooms["Room 1"]
        roomslot = room.availability[1]
        timeslot = roomslot.timeslot
        del schedule.class_sections[section.id]
        del section.teachers[0].taught_sections[section.id]
        section.teachers[0].availability.remove(timeslot)
        del section.teachers[0].availability_dict[
                (timeslot.start, timeslot.end)]
        timeslot.associated_roomslots.remove(roomslot)
        room.availability.remove(roomslot)
        room.flush_roomslot_caches()
        del room.availability_dict[(timeslot.start, timeslot.end)]
        schedule.run_consistency_checks()
        schedule.run_constraint_checks()

    def schedule_class_simple_db(self, lock=False):
        """Schedules section 0 in timeslot 1 of room 1.
        Returns said section, timeslot, and room.
        This operates on the database."""
        section_obj = ClassSection.objects.get(id=self.initial_section_id)
        timeslot = self.timeslots[1]
        room = Resource.objects.get(
            name="Room 1", res_type__name="Classroom", event=timeslot)
        # Make sure the room is available. If not, this is a bug in the test.
        assert room.is_available(), "Room wasn't available??"
        section_obj.assign_meeting_times([timeslot])
        section_obj.assign_room(room)
        if lock:
            module_ext.AJAXSectionDetail.objects.get_or_create(
                program=self.program, cls_id=section_obj.id, comment="locked",
                locked=True)
        return section_obj, timeslot, room

    def test_schedule_load(self):
        """Make sure that loading a schedule matches the schedule we
        constructed."""
        loaded_schedule = db_interface.load_schedule_from_db(self.program)
        self.assert_schedule_equality(loaded_schedule, self.schedule)

    def test_load_existing_class(self):
        """Make sure that existing classes are accounted for regardless of
        whether we specify to load existing classes. This means to either load
        them with the correct scheduling specified, or to block out the room's
        availability."""
        section_obj, event, room_obj = self.schedule_class_simple_db()
        self.remove_class_simple_model()
        loaded_schedule = db_interface.load_schedule_from_db(
            self.program, exclude_scheduled=True)
        room = loaded_schedule.classrooms[room_obj.name]
        # Assert that the room isn't available at that time.
        self.assertNotIn(event.id, [r.timeslot.id for r in room.availability])
        self.assert_schedule_equality(loaded_schedule, self.schedule)
        self.schedule = self.setUpSchedule(self.settings, self.extra_settings)
        self.schedule_class_simple_model(recompute_hash=True)
        loaded_schedule = db_interface.load_schedule_from_db(
            self.program, exclude_scheduled=False)
        self.assert_schedule_equality(loaded_schedule, self.schedule)

    def test_schedule_save(self):
        """Make a simple modification to the schedule and save it."""
        section, roomslot = self.schedule_class_simple_model()
        section_obj = ClassSection.objects.get(id=section.id)
        self.assertEqual(len(section_obj.get_meeting_times()), 0,
                         "Section already had meeting times")
        try:
            db_interface.save(self.schedule)
        except SchedulingError:
            self.fail("Schedule saving crashed with error: \n{}"
                      .format(traceback.format_exc()))
        self.assertEqual(len(section_obj.get_meeting_times()), 1,
                         "Section should have been scheduled for 1 timeslot")
        self.assertEqual(section_obj.get_meeting_times()[0].id,
                         roomslot.timeslot.id,
                         "Section was assigned to wrong timeslot")

    def test_schedule_double_save(self):
        """Test that saving twice in a row works."""
        self.schedule_class_simple_model()
        try:
            db_interface.save(self.schedule)
        except SchedulingError:
            self.fail("Schedule saving crashed with error: \n{}"
                      .format(traceback.format_exc()))
        try:
            db_interface.save(self.schedule)
        except SchedulingError:
            self.fail("Schedule second save crashed with error: \n{}"
                      .format(traceback.format_exc()))

    def test_load_lunch(self):
        """Make sure that lunch classes cause lunch timeslots to be loaded,
        but that we can exclude lunch classes. Note that we are NOT testing
        that we can successfully load lunch classes if we wanted."""
        lunch, created = ClassCategories.objects.get_or_create(
                category="Lunch", symbol="L")
        subj, created = ClassSubject.objects.get_or_create(
                title="Lunch!", category=lunch, grade_min=7, grade_max=12,
                parent_program=self.program, class_size_max=2000,
                class_info="Get fud!")
        subj.accept()
        lunch_timeslots = [self.timeslots[1], self.timeslots[2],
                           self.extra_timeslot]
        lunch_times = [(e.start, e.end) for e in lunch_timeslots]
        for i in xrange(3):
            subj.add_section(duration=self.settings["timeslot_length"] / 60.0)
        secs = subj.get_sections()
        for i, t in enumerate(lunch_timeslots):
            secs[i].assign_start_time(t)
        # We don't exclude scheduled because that would cause lunch to also
        # be incidentally excluded. This way, we can test lunch exclusion.
        loaded_schedule = db_interface.load_schedule_from_db(
                self.program, exclude_lunch=True, exclude_scheduled=False)
        # Since lunch should be excluded and we didn't change anything else,
        # and we aren't testing for equality on lunch blocks, the loaded
        # program should still be equivalent to the original one
        self.assert_schedule_equality(loaded_schedule, self.schedule)
        loaded_lunch = loaded_schedule.lunch_timeslots
        self.assertEqual(len(loaded_lunch), 2,
                         "Should have loaded lunch on 2 days")
        start = lunch_timeslots[0].start
        start_day = (start.year, start.month, start.day)
        self.assertIn(start_day, loaded_lunch,
                      "Couldn't find first day of lunch")
        day1 = loaded_lunch[start_day]
        self.assertEqual(len(day1), 2,
                         "Should have 2 lunch timeslots on day 1")
        for i, timeslot in enumerate(day1):
            self.assertEqual((timeslot.start, timeslot.end), lunch_times[i],
                             "Loaded lunch time was wrong")
        start2 = lunch_timeslots[2].start
        start_day2 = (start2.year, start2.month, start2.day)
        self.assertIn(start_day2, loaded_lunch,
                      "Cloudln't find second day of lunch")
        day2 = loaded_lunch[start_day2]
        self.assertEqual(len(day2), 1, "Should have 1 lunch timeslot on day 2")
        self.assertEqual((day2[0].start, day2[0].end), lunch_times[2],
                         "LOaded lunch time was wrong on day 2")

    def test_load_locked_class(self):
        """Make sure that we can choose to load a locked class or not."""
        section_obj, event, room_obj = self.schedule_class_simple_db(lock=True)
        self.remove_class_simple_model()
        loaded_schedule = db_interface.load_schedule_from_db(
            self.program, exclude_scheduled=False, exclude_locked=True)
        room = loaded_schedule.classrooms[room_obj.name]
        # Assert that the room isn't available at that time.
        self.assertNotIn(event.id, [r.timeslot.id for r in room.availability])
        self.assert_schedule_equality(loaded_schedule, self.schedule)
        self.schedule = self.setUpSchedule(self.settings, self.extra_settings)
        self.schedule_class_simple_model(recompute_hash=True)
        loaded_schedule = db_interface.load_schedule_from_db(
            self.program, exclude_scheduled=False, exclude_locked=False)
        self.assert_schedule_equality(loaded_schedule, self.schedule)

    def test_schedule_save_swap_and_rollback(self):
        """Schedules two classes and saves. Then swaps them and saves. Then
        swaps them again and saves, but the save crashes partway through.
        The crashing part is supposed to roll back the whole transaction.
        It's kind of brittle to the implementation, however, because it assumes
        that the check_can_schedule_sections function is called once at the
        beginning and once at the end."""
        sections = [self.schedule.class_sections[i] for i in xrange(
                self.initial_section_id, self.initial_section_id + 2)]
        room = self.schedule.classrooms["Room 1"]
        roomslots = room.availability[1:3]
        for s, r in zip(sections, roomslots):
            s.assign_roomslots([r])

        section_objs = [ClassSection.objects.get(id=s.id) for s in sections]
        for s in section_objs:
            self.assertEqual(len(s.get_meeting_times()), 0,
                             "Section already had meeting times")
        try:
            db_interface.save(self.schedule)
        except SchedulingError:
            self.fail("Schedule saving crashed with error: \n{}"
                      .format(traceback.format_exc()))
        for r, so in zip(roomslots, section_objs):
            self.assertEqual(
                    len(so.get_meeting_times()), 1,
                    "Section should have been scheduled for 1 timeslot but "
                    "was scheduled for {}".format(len(so.get_meeting_times())))
            self.assertEqual(so.get_meeting_times()[0].id,
                             r.timeslot.id,
                             "Section was assigned to wrong timeslot")

        for s in sections:
            s.clear_roomslots()
        for s, r in zip(sections, reversed(roomslots)):
            s.assign_roomslots([r])
            self.assertEqual(len(s.assigned_roomslots), 1)
        try:
            db_interface.save(self.schedule)
        except SchedulingError:
            self.fail("Schedule saving crashed with error: \n{}"
                      .format(traceback.format_exc()))
        for r, so in zip(reversed(roomslots), section_objs):
            self.assertEqual(
                    len(so.get_meeting_times()), 1,
                    "Section should have been scheduled for 1 timeslot but "
                    "was scheduled for {}".format(len(so.get_meeting_times())))
            self.assertEqual(so.get_meeting_times()[0].id,
                             r.timeslot.id,
                             "Section was assigned to wrong timeslot")

        # It looks like we don't have the mock package?? Oh well.
        rvs = [True, False]
        db_interface_can_schedule = db_interface.check_can_schedule_sections

        def raise_after_one():
            if not rvs.pop(0):
                raise SchedulingError("oops")
        db_interface.check_can_schedule_sections = \
            lambda x, y: raise_after_one()
        try:
            for s in sections:
                s.clear_roomslots()
            for s, r in zip(sections, roomslots):
                s.assign_roomslots([r])
            with self.assertRaises(SchedulingError):
                db_interface.save(self.schedule)
            # Nothing should have moved.
            for r, so in zip(reversed(roomslots), section_objs):
                self.assertEqual(
                        len(so.get_meeting_times()), 1,
                        "Section should have been scheduled for 1 timeslot "
                        "but was scheduled for {}".format(
                            len(so.get_meeting_times())))
                self.assertEqual(so.get_meeting_times()[0].id,
                                 r.timeslot.id,
                                 "Section was assigned to wrong timeslot")
            db_interface.check_can_schedule_sections = \
                db_interface_can_schedule
        except:
            db_interface.check_can_schedule_sections = \
                db_interface_can_schedule
            raise
