"""Contains helper functions to load and save from the database.

This should be the only place (other than the controller itself) where any
database interaction happens.
"""

import json
import logging

from django.db.models import Count
from django.db import transaction

from esp.resources.models import \
    ResourceType, Resource, ResourceAssignment, ResourceRequest
from esp.program.models import ClassSection
from esp.program.models.class_ import ACCEPTED
from esp.users.models import ESPUser, UserAvailability
from esp.cal.models import Event
from esp.program.modules import module_ext
from esp.tagdict.models import Tag

from esp.program.controllers.autoscheduler.exceptions import SchedulingError
from esp.program.controllers.autoscheduler.data_model import \
    AS_Schedule, AS_ClassSection, AS_Teacher, AS_Classroom, \
    AS_Timeslot, AS_RoomSlot, AS_ResourceType
from esp.program.controllers.autoscheduler import \
    util, config, resource_checker

logger = logging.getLogger(__name__)


@util.timed_func("db_interface_load_schedule_from_db")
def load_schedule_from_db(
        program, require_approved=True, exclude_lunch=True,
        exclude_walkins=True, exclude_scheduled=True, exclude_locked=True,
        **kwargs):
    """Loads an AS_Schedule based on the database of a program. exclude_locked
    means that classes locked on the AJAX scheduler are not loaded (and instead
    are blocked off as unavailable), and has nothing to do with the lock_level
    for a ResourceAssignment."""
    ESPUser.create_membership_methods()

    timeslots = sorted(
        batch_convert_events(program.getTimeSlots(), program))

    lunch_events = Event.objects.filter(
            meeting_times__parent_class__category__category="Lunch",
            meeting_times__parent_class__parent_program=program)

    lunch_timeslots = [(e.start, e.end) for e in lunch_events]

    schedule = AS_Schedule(program=program, timeslots=timeslots,
                           lunch_timeslots=lunch_timeslots,
                           exclude_locked=exclude_locked)

    schedule.class_sections, schedule.teachers, schedule.classrooms = (
        load_sections_and_teachers_and_classrooms(
            schedule, require_approved, exclude_lunch,
            exclude_walkins, exclude_scheduled, exclude_locked))

    schedule.run_consistency_checks()
    schedule.run_constraint_checks()

    return schedule


@util.timed_func("db_interface_load_sections_and_teachers_and_classrooms")
def load_sections_and_teachers_and_classrooms(
        schedule, require_approved, exclude_lunch,
        exclude_walkins, exclude_scheduled, exclude_locked):
    """Loads sections, teachers, and classrooms into the schedule from the
    database. Helper function for load_schedule_from_db, to make use of the
    schedule's construction of the timeslot dict."""
    logger.info("Loading")

    # Get all the approved class sections for the program
    sections = ClassSection.objects.filter(
            parent_class__parent_program=schedule.program,
            ).select_related()

    if require_approved:
        sections = sections.filter(status=ACCEPTED)
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

    logger.info("Filtered")

    # For all excluded sections, remove their availabilities. What literally
    # happens here is that teacher availabilities are removed for every
    # section, and then their availabilities are added back for all sections
    # that have been loaded in the constructor of the AS_ClassSection.

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
                "event__start").values_list(
                    "user__id", "event__start", "event__end", "event__id")
        for teacher, event_start, event_end, event_id \
                in user_availabilities:
            if teacher in teacher_ids:
                teaching = teaching_times_by_teacher[teacher]
                times = (event_start, event_end)
                if (event_id not in teaching
                        and times in schedule.timeslot_dict):
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
    logger.info("Teachers loaded")

    known_sections = {section.id: section for section in sections}
    rooms_by_section, meeting_times_by_section, requests_by_section = (
        load_section_assignments(known_sections))
    logger.info("Assignments loaded")
    # Load classrooms from groupedClassrooms
    classrooms = convert_classroom_resources(
            schedule.program.getClassrooms(), schedule.program,
            schedule.timeslot_dict, known_sections,
            rooms_by_section, meeting_times_by_section)
    logger.info("Classrooms loaded")

    section_teachers = sections.values_list("id", "parent_class__teachers")
    teachers_by_section = {section: [] for section in known_sections}
    for section, teacher in section_teachers:
        teachers_by_section[section].append(teachers[teacher])

    converted_sections = batch_convert_sections(
        sections, schedule.program, teachers_by_section,
        schedule.timeslot_dict, classrooms,
        rooms_by_section, meeting_times_by_section, requests_by_section)
    logger.info("Sections converted")

    sections_dict = {sec.id: sec for sec in converted_sections}
    logger.info("Sections dict loaded")

    # Return!
    return sections_dict, teachers, classrooms


@util.timed_func("db_interface_save")
def save(schedule, check_consistency=True, check_constraints=True):
    """Saves the schedule."""
    logger.info("Executing save.")
    if check_consistency:
        # Run a consistency check first.
        schedule.run_consistency_checks()
    if check_constraints:
        # Run a constraint check first.
        schedule.run_constraint_checks()

    # Find all sections which we've actually moved.
    changed_sections = set(
        section for section in schedule.class_sections.itervalues()
        if section.initial_state
        != section.scheduling_hash())
    # Note: we need to be careful not to cache anything after we save
    # because a rollback will not roll back the cache. Ideally we would flush
    # the relevant entries of cache but I don't know how to do that. (TODO)
    # Right now we simply try to avoid calling cached functions.
    with transaction.atomic():
        ajax_change_log = get_ajax_change_log(schedule.program)
        section_objs = ClassSection.objects.filter(
                id__in=[s.id for s in changed_sections]).select_related()

        # Compute meeting times, classroom, and potentially conflicting classes
        # for each class.
        section_infos = []
        for section_obj in section_objs:
            section = schedule.class_sections[section_obj.id]
            possible_conflicts = []
            for teacher in section.teachers:
                teacher_obj = ESPUser.objects.get(id=teacher.id)
                other_sections = teacher_obj.getTaughtSections(
                    schedule.program)
                possible_conflicts.append(
                        (teacher.id, [other for other in other_sections
                                      if other.id != section.id]))

            # Compute our meeting times and classroom
            if section.is_scheduled():
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
            else:
                meeting_times = []
                room_objs = []
            section_infos.append(
                (section, section_obj, possible_conflicts,
                 meeting_times, room_objs))

        # First, we check to make sure nobody moved any sections we want, and
        # unschedule them to ensure we don't get cross-conflicts.
        for so in section_objs:
            section = schedule.class_sections[so.id]
            ensure_section_not_moved(so, section)
            if len(section_obj.get_meeting_times()) > 0:
                unschedule_section(so, ajax_change_log)

        check_can_schedule_sections(section_infos, schedule)
        for (section, section_obj, possible_conflicts, meeting_times,
                room_objs) in section_infos:
            if section.is_scheduled():
                schedule_section(
                    section_obj, meeting_times, room_objs[0], ajax_change_log)

        # Check again in case something bad happened while we were saving.
        for so in section_objs:
            section = schedule.class_sections[so.id]
            section.recompute_hash()
            ensure_section_not_moved(so, section)
        check_can_schedule_sections(section_infos, schedule)


@util.timed_func("db_interface_check_can_schedule_sections")
def check_can_schedule_sections(section_infos, schedule):
    """Takes a section_infos, containing:
        (AS_ClassSection, ClassSection, [(teacher_id, [other_sections])],
        meeting_times, room_objs)
    and verifies the following for each section that we want to schedule:
        - That the teacher is not teaching another class at that time
        - That the rooms are not currently in use by another class
    A SchedulingError is thrown if any of thes occur, otherwise nothing
    happens. This function should avoid caching anything because the cached
    value won't get rolled back by the transaction"""
    locked_sections = set(module_ext.AJAXSectionDetail.objects.filter(
            program=schedule.program, locked=True).values_list(
                    "cls_id", flat=True))

    for section, section_obj, possible_conflicts, meeting_times, room_objs \
            in section_infos:
        if section.id in locked_sections:
            raise SchedulingError("Section {} is locked!".format(
                section_obj.emailcode()))
        if section.is_scheduled():
            start_time = section.assigned_roomslots[0].timeslot.start
            end_time = section.assigned_roomslots[-1].timeslot.end
            for teacher_id, other_sections in possible_conflicts:
                # Make sure the teacher isn't teaching
                for other_section in other_sections:
                    for other_time in other_section.meeting_times.all():
                        if not (other_time.start >= end_time
                                or other_time.end <= start_time):
                            raise SchedulingError(
                                "Teacher {} of section {} is already teaching "
                                "section {}".format(
                                    teacher_id, section_obj.emailcode(),
                                    other_section.emailcode()))

            # Make sure the room is available
            for room_obj in room_objs:
                if room_obj.is_taken():
                    occupiers = room_obj.assignments()
                    for occupier in occupiers:
                        other_section = occupier.target
                        if other_section.id != section.id:
                            raise SchedulingError(
                                "Destination room {} of section {} was "
                                "already occupied by section {}".format(
                                    room_obj.name, section_obj.emailcode(),
                                    other_section.emailcode()))


@util.timed_func("db_interface_ensure_section_not_moved")
def ensure_section_not_moved(section, as_section):
    """Ensures that a ClassSection hasn't moved, according to the record
    stored in its corresponding AS_Section. Raises a SchedulingError if it
    was moved, otherwise does nothing. This function should avoid caching
    anything to avoid a stale cache result not being rolled back"""
    assert section.id == as_section.id, "Unexpected ID mismatch"
    if scheduling_hash_of(section) != as_section.initial_state:
        raise SchedulingError(
                "Section {} was moved.".format(section.emailcode()))


@util.timed_func("db_interface_unschedule_section")
def unschedule_section(
        section, ajax_change_log, unscheduled_sections_log=None):
    """Unschedules a ClassSection and records it as needed."""
    logger.info("Unscheduling {}".format(section.emailcode()))
    section.clear_meeting_times()
    section.clearRooms()
    if unscheduled_sections_log is not None:
        unscheduled_sections_log.add(section.id)
    ajax_change_log.appendScheduling([], "", section.id, None)


@util.timed_func("db_interface_schedule_section")
def schedule_section(section, times, room, ajax_change_log):
    """Schedules the section in the times and rooms."""
    logger.info("Scheduling section.")
    section.assign_meeting_times(times)
    status, errors = section.assign_room(room)
    if not status:
        section.clear_meeting_times()
        raise SchedulingError(
                "Room assignment failed with errors: "
                + " | ".join(errors))
    ajax_change_log.appendScheduling(
        [t.id for t in times], room.name, section.id, None)


def get_ajax_change_log(prog):
    """Returns the AJAXChangeLog for a program. Duplicates logic from
    the ajaxschedulingmodule handler's get_change_log."""
    change_log = module_ext.AJAXChangeLog.objects.filter(program=prog)

    if change_log.count() == 0:
        change_log = module_ext.AJAXChangeLog()
        change_log.update(prog)
        change_log.save()
    else:
        change_log = change_log[0]

    return change_log


def convert_classection_obj(
        section, program, teachers_by_section, timeslot_dict, rooms,
        rooms_by_section, meeting_times_by_section,
        requests_by_section):
    """Create a AS_ClassSection from a ClassSection and Program. Will also
    populate the given dictionary of teachers and uses the given dictionary
    of timeslots for availabilities. """
    if not section_satisfies_constraints(
            section, rooms_by_section, meeting_times_by_section):
        logger.info("Warning: Autoscheduler can't handle section {}"
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
            teachers, float(section.duration), get_section_capacity(section),
            section.category.id, roomslots,
            section_id=section.id, parent_class_id=section.parent_class.id,
            grade_min=section.parent_class.grade_min,
            grade_max=section.parent_class.grade_max,
            resource_requests=resource_requests_dict)

    assert (scheduling_hash_of(
            section, rooms_by_section, meeting_times_by_section) ==
            as_section.initial_state), (
        "AS_ClassSection state doesn't match ClassSection state "
        "for section {}".format(section.emailcode()))

    return as_section


def get_section_capacity(section):
    if section.max_class_capacity is not None:
        return section.max_class_capacity
    else:
        return section.parent_class.class_size_max


@util.timed_func("db_interface_load_section_assignments")
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
    all_meeting_times = set(time for sec, time in meeting_times if time is
                            not None)
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
    return (rooms_by_section, meeting_times_by_section,
            requests_by_section)


@util.timed_func("db_interface_section_satisfies_constraints")
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
        scheduled_duration = util.hours_difference(start_time, end_time)
        if (abs(scheduled_duration - float(section_obj.duration))
                > config.DELTA_TIME):
            return False
    return True


@util.timed_func("db_interface_load_constraints")
def load_constraints(program, constraints_overrides=None):
    """Returns constraint names loading from defaults, the Tag in the
    db, and the given overrides, in increasing order of precedence."""
    if constraints_overrides is None:
        constraints_overrides = {}

    tag_value = Tag.getProgramTag(config.CONSTRAINT_TAG,
                                  program=program)

    try:
        tag_overrides = json.loads(tag_value)
    except ValueError as e:
        raise SchedulingError(
                "Constraints Tag is malformatted with error {}: {}" .format(
                    e, tag_value))

    return util.override(
        [config.DEFAULT_CONSTRAINTS_ENABLED,
         tag_overrides, constraints_overrides])


@util.timed_func("db_interface_load_scorers")
def load_scorers(program, scorer_overrides=None):
    """Returns scorer names and weights loading from defaults, the Tag in the
    db, and the given overrides, in increasing order of precedence."""
    if scorer_overrides is None:
        scorer_overrides = {}

    tag_value = Tag.getProgramTag(config.SCORER_TAG,
                                  program=program)

    try:
        tag_overrides = json.loads(tag_value)
    except ValueError as e:
        raise SchedulingError("Scoring Tag is malformatted with error {}: {}"
                              .format(e, tag_value))

    return util.override(
        [config.DEFAULT_SCORER_WEIGHTS, tag_overrides, scorer_overrides])


@util.timed_func("db_interface_load_resource_constraints")
def load_resource_constraints(
        program, specification_overrides=None, specs_only=False,
        ignore_comments=True):
    if specification_overrides is None:
        specification_overrides = {}

    tag_value = Tag.getProgramTag(config.RESOURCE_CONSTRAINTS_TAG,
                                  program=program)
    try:
        tag_overrides = json.loads(tag_value)
        if ignore_comments:
            tag_overrides = {
                k: v for k, v in tag_overrides.iteritems()
                if "_comment" not in k}
    except ValueError as e:
        raise SchedulingError(
            "Resource constraints Tag is malformatted with error {}: {}"
            .format(e, tag_value))
    specs = [config.DEFAULT_RESOURCE_CONSTRAINTS,
             tag_overrides,
             specification_overrides]
    if specs_only:
        return {
            name: spec for name, spec
            in util.override(specs).iteritems()
            if spec != "None" and spec is not None}
    else:
        valid_res_types = ResourceType.objects.filter(
            program=program).values_list("name", flat=True)
        return resource_checker.create_resource_criteria(
                specs, valid_res_types)


@util.timed_func("db_interface_load_resoure_scoring")
def load_resource_scoring(
        program, specification_overrides=None, specs_only=True,
        ignore_comments=True):
    if specification_overrides is None:
        specification_overrides = {}

    tag_value = Tag.getProgramTag(config.RESOURCE_SCORING_TAG,
                                  program=program)
    try:
        tag_overrides = json.loads(tag_value)
        if ignore_comments:
            tag_overrides = {
                k: v for k, v in tag_overrides.iteritems()
                if "_comment" not in k}
    except ValueError as e:
        raise SchedulingError(
            "Resource scoring Tag is malformatted with error {}: {}"
            .format(e, tag_value))

    specs = [config.DEFAULT_RESOURCE_SCORING,
             tag_overrides,
             specification_overrides]
    if specs_only:
        return {
            name: (spec, weight) for name, (spec, weight)
            in util.override(specs).iteritems()
            if spec != "None" and spec is not None}
    else:
        valid_res_types = ResourceType.objects.filter(
            program=program).values_list("name", flat=True)
        return resource_checker.create_resource_criteria(
                specs, valid_res_types, use_weights=True)


@util.timed_func("db_interface_batch_convert_sections")
def batch_convert_sections(
        sections, program, teachers_by_section, timeslot_dict, rooms,
        rooms_by_section, meeting_times_by_section,
        requests_by_section):
    converted_sections = []
    for s_obj in sections:
        s = convert_classection_obj(
            s_obj, program, teachers_by_section,
            timeslot_dict, rooms, rooms_by_section,
            meeting_times_by_section, requests_by_section)
        if s is not None:
            converted_sections.append(s)
    return converted_sections


@util.timed_func("db_interface_scheduling_hash_of")
def scheduling_hash_of(
        section, rooms_by_section=None, meeting_times_by_section=None):
    """Creates a unique hash based on the timeslots and rooms assigned to a
    section."""
    if meeting_times_by_section is not None:
        meeting_times = meeting_times_by_section[section.id]
    else:
        meeting_times = section.meeting_times.all()
    meeting_times = sorted([(str(e.start), str(e.end))
                            for e in meeting_times])
    rooms = (rooms_by_section[section.id] if rooms_by_section is not None
             else section.classrooms())
    rooms = sorted(list(set(r.name for r in rooms)))
    return json.dumps([meeting_times, rooms])


@util.timed_func("db_interface_convert_classroom_resources")
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

    classroom_restype = ResourceType.get_or_create("Classroom")
    for classroom in classrooms:
        assert classroom.res_type == classroom_restype
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
                furnishing_objs = (
                    furnishings_by_group[classroom.res_group_id]
                    if classroom.res_group_id is not None else [])
                furnishings = batch_convert_resources(
                    furnishing_objs)
                furnishings_dict = {r.name: r for r in furnishings}
                classroom_info_dict[classroom.name] = (
                    ([], classroom.num_students, furnishings_dict))
            event = classroom.event
            timeslot = timeslot_dict[(event.start, event.end)]
            classroom_info_dict[classroom.name][0].append(timeslot)
    classroom_dict = {}
    for room in classroom_info_dict:
        timeslots, capacity, furnishings = classroom_info_dict[room]
        classroom_dict[room] = AS_Classroom(
            room, capacity, timeslots, furnishings)
    return classroom_dict


def convert_event(event, program):
    """Create an AS_Timeslot from an Event."""
    assert event.parent_program() == program, \
        "Event parent program doesn't match"
    assert event.start < event.end, "Timeslot doesn't end after start time"
    return AS_Timeslot(event.start, event.end, event.id, None)


@util.timed_func("db_interface_batch_convert_events")
def batch_convert_events(events, program):
    return [convert_event(e, program) for e in events]


@util.timed_func("db_interface_batch_find_events")
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


@util.timed_func("db_interface_batch_convert_roomslots")
def batch_convert_roomslots(events, room, timeslot_dict):
    return [AS_RoomSlot(timeslot_dict[(e.start, e.end)], room) for e in events]


def convert_restypes(restype, value=""):
    """Create an AS_ResourceType from a ResourceType"""
    return AS_ResourceType(restype.name, restype.id, value)


@util.timed_func("db_interface_batch_convert_resource_requests")
def batch_convert_resource_requests(res):
    """Converts from ResourceRequests to AS_ResourceTypes."""
    return [convert_restypes(r.res_type, r.desired_value) for r in res]


@util.timed_func("db_interface_batch_convert_resources")
def batch_convert_resources(res):
    """Converts from Resources to AS_ResourceTypes."""
    return [convert_restypes(r.res_type, r.attribute_value) for r in res]
