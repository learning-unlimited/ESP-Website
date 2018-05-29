"""Classes for representing a schedule in-memory.

Mostly reflects the database on the rest of the website, but having separate
models should be a bit more robust to changes in website structure and should
also be more performant.  """

import bisect
from functools import total_ordering
import json

import esp.program.controllers.autoscheduler.config as config
from esp.program.controllers.autoscheduler.consistency_checks import \
        ConsistencyChecker
from esp.program.controllers.autoscheduler.constraints import \
        CompositeConstraint
from esp.program.controllers.autoscheduler.exceptions import SchedulingError
import esp.program.controllers.autoscheduler.util as util


class AS_Schedule(object):
    def __init__(self, program=None, timeslots=None, class_sections=None,
                 teachers=None, classrooms=None, lunch_timeslots=None,
                 required_resource_criteria=None,
                 optional_resource_criteria=None, constraints=None,
                 exclude_locked=True):
        """Argument types:
         - program is a Program object
         - timeslots is a sorted list of AS_Timeslots
         - class_sections is a dict of {section_id: AS_ClassSection}
         - teachers is a dict of {teacher_id: AS_Teacher}
         - classrooms is a dict of {classroom_name: AS_Classroom}
         - lunch_timeslots is a list of (lunch_start, lunch_end).
         - constraints is a subclass of BaseConstraint (e.g.
           CompositeConstraint)
         - exclude_locked is a boolean; it doesn't do anything here,
                and is only for use in db_interface.save().
        """
        self.program = program
        self.timeslots = timeslots if timeslots is not None else []

        # Maps from start and end times to a timeslot.
        self.timeslot_dict = self.build_timeslot_dict()
        # Dict of class sections by ID
        self.class_sections = class_sections if class_sections is not None \
            else {}
        # Dict of teachers by ID
        self.teachers = teachers if teachers is not None else {}
        # Dict of classrooms by name
        self.classrooms = classrooms if classrooms is not None else {}
        # A dict of lunch timeslots by day, i.e maps from (year, month, day)
        # to a list of timeslots. Timeslots should also be in timeslot_dict.
        self.lunch_timeslots = self.build_lunch_timeslots(
                lunch_timeslots if lunch_timeslots is not None else [])
        # We have constraints here more or less as an extra set of consistency
        # checks.
        self.constraints = constraints if constraints is not None else \
            CompositeConstraint([])

        self.exclude_locked = exclude_locked

        self.run_consistency_checks()
        self.run_constraint_checks()

    def build_timeslot_dict(self):
        return {(t.start, t.end): t for t in self.timeslots}

    def build_lunch_timeslots(self, lunch_timeslots):
        timeslots_by_day = {}
        for (start, end) in sorted(lunch_timeslots):
            if (start, end) not in self.timeslot_dict:
                continue
            day = (start.year, start.month, start.day)
            if day not in timeslots_by_day:
                timeslots_by_day[day] = []
            assert (end.year, end.month, end.day) == day, \
                "Timeslot spans multiple days"
            timeslots_by_day[day].append(self.timeslot_dict[(start, end)])
        return timeslots_by_day

    def run_consistency_checks(self):
        ConsistencyChecker().run_all_consistency_checks(self)

    def run_constraint_checks(self):
        violation = self.constraints.check_schedule(self)
        if violation is not None:
            raise SchedulingError(
                ("Schedule violated constraints: {}. If this is intended, "
                 "consider locking the offending class(es)."
                 .format(violation)))


class AS_ClassSection(object):
    def __init__(self, teachers, duration, capacity,
                 category, assigned_roomslots,
                 section_id, parent_class_id,
                 grade_min=7, grade_max=12,
                 resource_requests=None):
        self.id = section_id
        self.parent_class = parent_class_id
        # Duration, in hours.
        self.duration = duration
        # A list of teachers.
        self.teachers = teachers
        # Capacity, an int.
        self.capacity = capacity
        # Min and max grade, integers
        self.grade_min = grade_min
        self.grade_max = grade_max
        # Category ID
        self.category = category
        # A sorted list of assigned roomslots.
        self.assigned_roomslots = assigned_roomslots
        for roomslot in assigned_roomslots:
            roomslot.assigned_section = self
            for teacher in self.teachers:
                teacher.add_availability(roomslot.timeslot)
        # Dict from restype names to AS_Restypes requested
        self.resource_requests = resource_requests \
            if resource_requests is not None else {}

        # A hash of the initial state.
        self.recompute_hash()
        self.register_teachers()

    def register_teachers(self):
        """Makes sure that all teachers have this section listed in their taught
        sections."""
        for teacher in self.teachers:
            teacher.taught_sections[self.id] = self

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

    def recompute_hash(self):
        self.initial_state = self.scheduling_hash()

    def scheduling_hash(self):
        """Creates a unique string based on the timeslots and rooms assigned to
        this section. It's not actually a hash anymore, but renaming sounds
        like a pain"""
        meeting_times = sorted([(str(e.timeslot.start), str(e.timeslot.end))
                                for e in self.assigned_roomslots])
        rooms = sorted(list(set(r.room.name for r in
                                self.assigned_roomslots)))
        return json.dumps([meeting_times, rooms])


class AS_Teacher(object):
    def __init__(self, availability, teacher_id, is_admin=False):
        self.id = teacher_id
        self.availability = availability if availability is not None \
            else []
        # Dict from section ID to section
        self.taught_sections = {}
        self.is_admin = is_admin
        self.availability_dict = {
            (t.start, t.end): t for t in self.availability}

    def add_availability(self, timeslot):
        if (timeslot.start, timeslot.end) not in self.availability_dict:
            bisect.insort_left(self.availability, timeslot)
            self.availability_dict[(timeslot.start, timeslot.end)] = timeslot


class AS_Classroom(object):
    def __init__(self, name, capacity, available_timeslots,
                 furnishings=None):
        self.name = name
        self.capacity = capacity
        # Availabilities as roomslots, sorted by the associated timeslot.
        # Does not account for sections the scheduler knows are scheduled.
        # Note that if you modify this, you need to invalidate roomslot
        # next-roomslot caching.
        self.availability = [AS_RoomSlot(timeslot, self) for timeslot in
                             sorted(available_timeslots)]
        # Dict of resources available in the classroom, mapping from the
        # resource name to AS_Restype.
        self.furnishings = furnishings if furnishings is not None else {}
        self.availability_dict = {(r.timeslot.start, r.timeslot.end): r
                                  for r in self.availability}
        if len(self.availability_dict) != len(self.availability):
            raise SchedulingError(
                "Room {} has duplicate resources".format(name))

    @util.timed_func("AS_Classroom_get_roomslots_by_duration")
    @util.memoize
    def get_roomslots_by_duration(self, start_roomslot, duration):
        """Given a starting roomslot, returns a list of roomslots that
        will cover the length of time specified by duration. If unable
        to do so, return as many roomslots as possible."""
        list_of_roomslots = [start_roomslot]
        classroom_availability = start_roomslot.room.availability
        if start_roomslot not in classroom_availability:
            return []
        index_of_roomslot = start_roomslot.index()
        start_time = start_roomslot.timeslot.start
        end_time = start_roomslot.timeslot.end
        while duration - util.hours_difference(start_time, end_time)\
                > config.DELTA_TIME:
            index_of_roomslot += 1
            if index_of_roomslot >= len(classroom_availability):
                break
            current_roomslot = classroom_availability[index_of_roomslot]
            list_of_roomslots.append(current_roomslot)
            end_time = current_roomslot.timeslot.end
        return list_of_roomslots

    def load_roomslot_caches(self):
        """Calls index() and next() for all roomslots to load their caches.
        This is mostly for testing purposes."""
        for roomslot in self.availability:
            roomslot.index()
            roomslot.next()

    def flush_roomslot_caches(self):
        """Flush each roomslot's caches for their next_roomslot and index
        values."""
        for roomslot in self.availability:
            roomslot.flush_cache()


# Ordered by start time, then by end time.
@total_ordering
class AS_Timeslot(object):
    """A timeslot, not specific to any teacher or class or room."""
    def __init__(self, start, end, event_id, associated_roomslots=None):
        self.id = event_id
        self.start = start
        self.end = end
        self.duration = util.hours_difference(start, end)
        # AS_RoomSlots during this timeslot
        self.associated_roomslots = associated_roomslots \
            if associated_roomslots is not None else set()
        if self.duration < config.DELTA_TIME:
            raise SchedulingError(
                "Timeslot duration {} is too short".format(self.duration))

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


class AS_RoomSlot(object):
    """A specific timeslot where a specific room is available."""
    def __init__(self, timeslot, room):
        self.timeslot = timeslot
        timeslot.associated_roomslots.add(self)
        self.room = room
        self.assigned_section = None

        # These next two properties are cached when their getter functions are
        # first called. As a corollary, their getter functions shouldn't be
        # called until the availability is finalized, and the availability
        # shouldn't be changed afterwards unless the cache is flushed. This is
        # pretty sketchy, which is why we have consistency checks for them.
        # The classroom's next roomslot.
        self._next_is_cached = False
        self._next = None
        # The index of this roomslot in the classroom's availability.
        self._index = None

    def index(self):
        if self._index is None:
            self._index = self.room.availability.index(self)
        return self._index

    def next(self):
        if not self._next_is_cached:
            idx = self.index()
            if idx == len(self.room.availability) - 1:
                self.next_roomslot = None
            else:
                self.next_roomslot = \
                    self.room.availability[idx + 1]
            self._next_is_cached = True
        return self.next_roomslot

    def flush_cache(self):
        """Flushes the caches for index and next. Floosh!"""
        self._index = None
        self._next_is_cached = False


class AS_ResourceType(object):
    def __init__(self, name, restype_id, value=""):
        self.id = restype_id
        self.name = name
        self.value = value  # Not in use yet
