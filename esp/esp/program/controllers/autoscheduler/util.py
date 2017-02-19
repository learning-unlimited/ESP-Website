"""
Various utility functions.
"""

from datetime import timedelta, datetime
from timeit import default_timer

from esp.program.controllers.autoscheduler import config


TIMES = {}


def timed_func(key):
    if not config.USE_TIMER:
        return lambda x: x
    """Generates a decorator which times a function and records its total time
    under the specified key."""
    if key not in TIMES:
        TIMES[key] = 0.0

    def timer(func):
        def wrapper(*args, **kwargs):
            start = default_timer()
            retval = func(*args, **kwargs)
            end = default_timer()
            TIMES[key] += (end - start)
            return retval
        return wrapper
    return timer


def total_time_recorded(key):
    """Returns the total time recorded under the key."""
    return TIMES.get(key, None)


def contiguous(timeslot1, timeslot2):
    """
    Checks whether two AS_Timeslots are contiguous.

    Returns true if the second argument is less than 20 minutes apart
    from the first one.

    Duplicates logic from esp.cal.Event.
    """
    tol = timedelta(minutes=20)

    if (timeslot2.start < timeslot1.end):
        return False
    if (timeslot2.start - timeslot1.end) < tol:
        return True
    else:
        return False


def get_min_id(objects):
    """Gets the minimum ID from a list of objects."""
    return min([o.id for o in objects])


def hours_difference(datetime1, datetime2):
    """Returns the number of hours between two datetime objects."""
    return (datetime2 - datetime1).total_seconds() / 3600.0


def override(dicts):
    """Given list of dicts, overrides values from left to right, i.e. last dict
    in key has highest precedence."""
    output = {}
    for d in dicts:
        for k, v in d.iteritems():
            output[k] = v
    return output


def datetimedump(dt):
    """Turns a datetime object into a json-like object loadable by
    datetimeload."""
    return list(dt.utctimetuple())[:6]


def datetimeloads(dt_tuple):
    """Turns a json-like datetime dump into a datetime object."""
    return datetime(*dt_tuple)
