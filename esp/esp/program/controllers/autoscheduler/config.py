
""" The maximum allowed time gap between two consecutive timeslots, in hours,
which is also the minimum allowed length of a timeslot."""
DELTA_TIME = 0.34


"""*******************Scoring**********************"""
"""Default scorer names and weights for scorers. Format is:
    ScorerClassName: weight
This will be overridden by a tag, and then by user input. To not use a scorer,
set its weight to 0. Note that in addition to these weights, each scorer has a
scaling so that each 'relevant' section has weight 1/num_sections. See the
docstring at the top of scoring.py for details. These weights therefore impose
a loose per-section importance ranking on the scorers."""
DEFAULT_SCORER_WEIGHTS = {
        "AdminDistributionScorer": 70.0,
        "CategoryBalanceScorer": 10.0,
        "LunchStudentClassHoursScorer": 20.0,
        "HungryTeacherScorer": 70.0,
        "NumSectionsScorer": 100.0,
        "NumSubjectsScorer": 60.0,
        "NumTeachersScorer": 50.0,
        "ResourceCriteriaScorer": 40.0,
        "ResourceMatchingScorer": 20.0,
        "ResourceValueMatchingScorer": 20.0,
        "RoomConsecutivityScorer": 10.0,
        "RoomSizeMismatchScorer": 30.0,
        "StudentClassHoursScorer": 50.0,
        "TeachersWhoLikeRunningScorer": 10.0
}

SCORER_TAG = "autoscheduler_scorer_weight_overrides"


"""********************Resources********************"""

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

"""Default ResourceCriteria used for scoring. Format is:
    name: (specification, weight)
See the comment on DEFAULT_RESOURCE_CONSTRAINTS for more details. Weights are
all relative, and the total weight will be determined by the total weight of
the ResourceCriteriaScorer."""
DEFAULT_RESOURCE_SCORING = {
    # Nothing here, since ResourceMatchingScorer and
    # ResourceValueMatchingScorer should cover generic cases.
}

RESOURCE_SCORING_TAG = "autoscheduler_resource_scoring_overrides"
