"""Various utility functions."""

from datetime import timedelta, datetime
from timeit import default_timer
from functools import wraps

from esp.program.controllers.autoscheduler import config


TIMES = {}


class Timer(object):
    def __init__(self):
        self.stack = []
        self.times = []
        self.last_started = None

    def update_time(self):
        time = default_timer()
        if len(self.stack) > 0:
            self.times[-1] += time - self.last_started
        self.last_started = time

    def start(self, key):
        self.update_time()
        self.stack.append(key)
        self.times.append(0)

    def end(self, key):
        assert self.stack[-1] == key, "Wasn't a stack"
        self.update_time()
        TIMES[key][0] += self.times[-1]
        TIMES[key][1] += 1
        self.times.pop()
        self.stack.pop()


TIMER = Timer()


def timed_func(key):
    """Generates a decorator which times a function (but not including
    subroutines that are also timed) and records its total time
    under the specified key."""

    if not config.USE_TIMER:
        return lambda x: x  # Decorator does nothing
    if key not in TIMES:
        TIMES[key] = [0.0, 0]

    def timer(func):
        def wrapper(*args, **kwargs):
            TIMER.start(key)
            retval = func(*args, **kwargs)
            TIMER.end(key)
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


def memoize(f):
    """Memoizes a function that doesn't take kwargs."""
    cache = {}

    @wraps(f)
    def memoized_f(*args):
        if args not in cache:
            cache[args] = f(*args)
        return cache[args]
    return memoized_f
