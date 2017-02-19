class ConsistencyError(Exception):
    """An error caught by a consistency check."""
    pass


class SchedulingError(Exception):
    """An error trying to load or save a schedule."""
    pass
