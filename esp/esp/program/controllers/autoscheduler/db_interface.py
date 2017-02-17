"""
Contains helper functions to load and save from the database. This should be
the only place where any database interaction happens.
"""

import hashlib
import json

from django.db.models import Count
from django.db import transaction

from esp.resources.models import \
    ResourceType, Resource, ResourceAssignment, ResourceRequest
from esp.program.models import ClassSection
from esp.users.models import ESPUser, UserAvailability
from esp.cal.models import Event
from esp.program.modules import module_ext

from esp.program.controllers.autoscheduler.exceptions import SchedulingError
from esp.program.controllers.autoscheduler.models import \
    AS_Schedule, AS_ClassSection, AS_Teacher, AS_Classroom, \
    AS_Timeslot, AS_RoomSlot, AS_ResourceType
from esp.program.controllers.autoscheduler import util
import esp.program.controllers.autoscheduler.constants as constants


def load_schedule_from_db(
        program, require_approved=True, exclude_lunch=True,
        exclude_walkins=True, exclude_scheduled=True, exclude_locked=True):
    ESPUser.create_membership_methods()

    timeslots = \
        sorted(batch_convert_events(program.getTimeSlots(), program))

    lunch_events = Event.objects.filter(
            meeting_times__parent_class__category__category="Lunch",
            meeting_times__parent_class__parent_program=program)

    lunch_timeslots = [(e.start, e.end) for e in lunch_events]

    schedule = AS_Schedule(program=program, timeslots=timeslots,
                           lunch_timeslots=lunch_timeslots)

    schedule.class_sections, schedule.teachers, schedule.classrooms = \
        load_sections_and_teachers_and_classrooms(
            schedule, require_approved, exclude_lunch,
            exclude_walkins, exclude_scheduled, exclude_locked)

    schedule.run_consistency_checks()
    schedule.run_constraint_checks()

    return schedule


def load_sections_and_teachers_and_classrooms(
        schedule, require_approved, exclude_lunch,
        exclude_walkins, exclude_scheduled, exclude_locked):
    """Loads sections, teachers, and classrooms into the schedule from the
    database. Helper function for load_schedule_from_db, to make use of the
    schedule's construction of the timeslot dict."""
    print "Loading"

    # Get all the approved class sections for the program
    sections = ClassSection.objects.filter(
            parent_class__parent_program=schedule.program,
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
                parent_class__category=schedule.program.open_class_category)
    if exclude_locked:
        locked_sections = module_ext.AJAXSectionDetail.objects.filter(
            program=schedule.program, locked=True).values_list(
                    "cls_id", flat=True)
        sections = sections.exclude(id__in=locked_sections)

    print "Filtered"

    # For all excluded sections, remove their availabilities

    teacher_ids = sections.values_list("parent_class__teachers", flat=True)
    teaching_times = ClassSection.objects.filter(
        parent_class__parent_program=schedule.program).values_list(
            "parent_class__teachers", "meeting_times")
    teaching_times_by_teacher = {teacher: set() for teacher in teacher_ids}
    availabilities_by_teacher = {teacher: [] for teacher in teacher_ids}
    for teacher, time in teaching_times:
        if time is not None and teacher in teaching_times_by_teacher:
            teaching_times_by_teacher[teacher].add(time)
    if schedule.program.hasModule("AvailabilityModule"):
        user_availabilities = UserAvailability.objects.filter(
            event__program=schedule.program).order_by(
                "event__start").select_related()
        for availability in user_availabilities:
            teacher = availability.user.id
            if teacher in teacher_ids:
                event = availability.event
                teaching = teaching_times_by_teacher[teacher]
                times = (event.start, event.end)
                if event.id not in teaching \
                        and times in schedule.timeslot_dict:
                    availabilities_by_teacher[teacher].append(
                        schedule.timeslot_dict[times])
    else:
        for teacher in availabilities_by_teacher:
            teaching = teaching_times_by_teacher[teacher]
            availabilities_by_teacher[teacher] = [
                t for t in schedule.timeslots if t.id not in teaching]
    admins = set(
        ESPUser.objects.filter(groups__name="Administrator").values_list(
            "id", flat=True))
    teachers = {
        teacher: AS_Teacher(
            availabilities_by_teacher[teacher], teacher, teacher in admins)
        for teacher in teacher_ids}
    print "Teachers loaded"

    known_sections = {section.id: section for section in sections}
    rooms_by_section, meeting_times_by_section, requests_by_section = \
        load_section_assignments(known_sections)
    print "Assignments loaded"
    # Load classrooms from groupedClassrooms
    classrooms = convert_classroom_resources(
            schedule.program.getClassrooms(), schedule.program,
            schedule.timeslot_dict, known_sections,
            rooms_by_section, meeting_times_by_section)
    print "Classrooms loaded"

    section_teachers = sections.values_list("id", "parent_class__teachers")
    teachers_by_section = {section: [] for section in known_sections}
    for section, teacher in section_teachers:
        teachers_by_section[section].append(teachers[teacher])

    converted_sections = batch_convert_sections(
        sections, schedule.program, teachers_by_section,
        schedule.timeslot_dict, classrooms,
        rooms_by_section, meeting_times_by_section, requests_by_section)
    print "Sections converted"

    sections_dict = {sec.id: sec for sec in converted_sections}
    print "Sections dict loaded"

    # Return!
    return sections_dict, teachers, classrooms


def save(schedule, check_consistency=True, check_constraints=True):
    """Saves the schedule."""
    if check_consistency:
        # Run a consistency check first.
        schedule.run_consistency_checks()
    if check_constraints:
        # Run a constraint check first.
        schedule.run_constraint_checks()

    # Find all sections which we've actually moved.
    changed_sections = set(
        [section for section in schedule.class_sections.itervalues()
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
                ensure_section_not_moved(section_obj, section)
            if section.is_scheduled():
                start_time = section.assigned_roomslots[0].timeslot.start
                end_time = section.assigned_roomslots[-1].timeslot.end
                # Make sure the teacher is available
                for teacher in section.teachers:
                    teacher_obj = ESPUser.objects.get(id=teacher.id)
                    other_sections = \
                        teacher_obj.getTaughtSections(schedule.program)
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
                            try_unschedule_section(
                                other_section, unscheduled_sections,
                                schedule.class_sections, err_msg)

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
                            try_unschedule_section(
                                    other_section, unscheduled_sections,
                                    schedule.class_sections,
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


def try_unschedule_section(section, unscheduled_sections, class_sections,
                           error_message):
    """Tries to unschedule the given ClassSection. If it's not in the list
    of known sections (class_sections), throw a SchedulingError with the
    given error message. Otherwise, make sure the section wasn't moved by
    external sources, and unschedule it."""
    if section.id not in class_sections:
        raise SchedulingError(error_message)
    else:
        ensure_section_not_moved(
                section, class_sections[section.id])
        unschedule_section(section, unscheduled_sections)


def ensure_section_not_moved(section, as_section):
    """Ensures that a ClassSection hasn't moved, according to the record
    stored in its corresponding AS_Section. Raises a SchedulingError if it
    was moved, otherwise does nothing."""
    assert section.id == as_section.id, "Unexpected ID mismatch"
    if scheduling_hash_of(section) != as_section.initial_state:
        raise SchedulingError("Section {} was \
                moved.".format(section.emailcode))


def unschedule_section(section, unscheduled_sections_log=None):
    """Unschedules a ClassSection and records it as needed."""
    # Unschedule the offending section.
    section.clear_meeting_times()
    section.clearRooms()
    if unscheduled_sections_log is not None:
        unscheduled_sections_log.add(section.id)


def convert_classection_obj(
        section, program, teachers_by_section, timeslot_dict, rooms,
        rooms_by_section, meeting_times_by_section,
        requests_by_section):
    """Create a AS_ClassSection from a ClassSection and Program. Will also
    populate the given dictionary of teachers and uses the given dictionary
    of timeslots for availabilities. """
    if not section_satisfies_constraints(
            section, rooms_by_section, meeting_times_by_section):
        print ("Warning: Autoscheduler can't handle section {}"
               .format(section.emailcode()))
        return None

    teachers = teachers_by_section[section.id]

    resource_requests = batch_convert_resource_requests(
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

    assert scheduling_hash_of(
            section, rooms_by_section, meeting_times_by_section) == \
        as_section.initial_state, \
        ("AS_ClassSection state doesn't match ClassSection state "
         "for section {}".format(section.emailcode()))

    return as_section


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


def batch_convert_sections(
        sections, program, teachers_by_section, timeslot_dict, rooms,
        rooms_by_section, meeting_times_by_section,
        requests_by_section):
    return [s for s in
            map(lambda s: convert_classection_obj(
                s, program, teachers_by_section, timeslot_dict, rooms,
                rooms_by_section, meeting_times_by_section,
                requests_by_section), sections)
            if s is not None]


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


def convert_classroom_resources(
        classrooms, program, timeslot_dict, known_sections,
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
            elif not section_satisfies_constraints(
                    known_sections[target],
                    rooms_by_section, meeting_times_by_section):
                unavailable = True
        if not unavailable:
            if classroom.name not in classroom_info_dict:
                furnishing_objs = \
                    furnishings_by_group[classroom.res_group_id] \
                    if classroom.res_group_id is not None else []
                furnishings = batch_convert_resources(
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


def convert_event(event, program):
    """Create an AS_Timeslot from an Event."""
    assert event.parent_program() == program, \
        "Event parent program doesn't match"
    assert event.start < event.end, "Timeslot doesn't end after start time"
    return AS_Timeslot(event.start, event.end, event.id, None)


def batch_convert_events(events, program):
    return map(lambda e: convert_event(e, program), events)


def batch_find_events(events, timeslot_dict):
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


def batch_convert_roomslots(events, room, timeslot_dict):
    return map(lambda e: AS_RoomSlot(
        timeslot_dict[(e.start, e.end)], room), events)


def convert_restypes(restype, value=""):
    """Create an AS_ResourceType from a ResourceType"""
    return AS_ResourceType(restype.name, restype.id, value)


def batch_convert_resource_requests(res):
    """Converts from ResourceRequests to AS_ResourceTypes."""
    return map(
        lambda r: convert_restypes(r.res_type, r.desired_value), res)


def batch_convert_resources(res):
    """Converts from Resources to AS_ResourceTypes."""
    return map(
        lambda r: convert_restypes(r.res_type, r.attribute_value), res)
