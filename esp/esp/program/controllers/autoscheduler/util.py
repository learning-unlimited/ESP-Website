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

    if (timeslot2.start - timeslot2.end) < tol:
        return True
    else:
        return False


def get_min_id(objects):
    """Gets the minimum ID from a list of objects."""
    return min([o.id for o in objects])
