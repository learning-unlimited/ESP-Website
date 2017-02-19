
""" The maximum allowed time gap between two consecutive timeslots, in hours,
which is also the minimum allowed length of a timeslot."""
DELTA_TIME = 0.34

"""Default ResourceCriteria used for constraints. Format is:
    name: specification
See resource_checker.ResourceCriterion for details on the specification. The
name is for overriding purposes, i.e. to override a particular criterion,
create another with the same name in an override dict. To delete a criterion in
an override, use None (either None or 'None' is okay) for the specification."""

DEFAULT_RESOURCE_CONSTRAINTS = {
    # If you don't want to use a classroom, mark its name with a star.
    "restrict_star_classrooms":
        "if any section then not classroom matches {}".format(
            r"^\*.*$")
}

RESOURCE_CONSTRAINTS_TAG = "autoscheduler_resource_constraint_overrides"
