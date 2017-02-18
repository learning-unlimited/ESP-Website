"""
Tools for running tests.
"""

from datetime import datetime

from esp.program.controllers.autoscheduler import models


def create_test_schedule_1():
    timeslots = [models.AS_Timeslot(
        datetime(2017, 2, 2, 10+i, 5),
        datetime(2017, 2, 2, 10+i, 55),
        event_id=i + 1) for i in xrange(6)]
    restype = models.AS_ResourceType("Projector", 0, "Yes")
    classrooms = {
        "26-100": models.AS_Classroom("26-100", 50, timeslots),
        "10-250": models.AS_Classroom("10-250", 30, timeslots[3:],
                                      furnishings={restype.name: restype})
    }
    teachers = {
        1: models.AS_Teacher(list(timeslots), 1, True),
        2: models.AS_Teacher(timeslots[:3], 2),
        3: models.AS_Teacher(timeslots[1:], 3)
    }
    sections = {
        1: models.AS_ClassSection([teachers[1]], 0.83, 20, 0, [], 1,
                                  resource_requests={restype.name: restype}),
        2: models.AS_ClassSection(
            [teachers[2], teachers[3]], 1.83, 50, 1, [], 2)}
    return models.AS_Schedule(timeslots=timeslots, class_sections=sections,
                              teachers=teachers, classrooms=classrooms)


def create_test_schedule_2():
    sched = create_test_schedule_1()
    classroom = sched.classrooms["26-100"]
    sched.class_sections[2].assign_roomslots(classroom.availability[1:3])
    return sched


def create_test_schedule_3():
    sched = create_test_schedule_1()
    timeslots_extra = [models.AS_Timeslot(
        datetime(2017, 2, 3, 10+i, 5),
        datetime(2017, 2, 3, 10+i, 55),
        event_id=i + 7) for i in xrange(6)]
    sched.timeslots += timeslots_extra
    sched.timeslot_dict = sched.build_timeslot_dict()
    lunch_timeslots = {
            (2017, 2, 2): [sched.timeslots[2], sched.timeslots[3]],
            (2017, 2, 3): [sched.timeslots[8], sched.timeslots[9]]}
    sched.lunch_timeslots = lunch_timeslots
    return sched
