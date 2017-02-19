"""
Various utility functions.
"""

from datetime import timedelta


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
