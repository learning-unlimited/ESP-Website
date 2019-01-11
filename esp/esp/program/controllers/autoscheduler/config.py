
# The maximum allowed time gap between two consecutive timeslots, in hours,
# which is also the minimum allowed length of a timeslot.
DELTA_TIME = 0.34


"""*******************Constraints*******************"""
# Default configuration for whether constraints are enabled. Format is:
#     ConstraintClassName: True/False
# This will be overridden by a tag, and then by user input. Note that this will
# only have an effect on optional constraints; see the docstring at the top of
# constraints.py for more details.
DEFAULT_CONSTRAINTS_ENABLED = {
    "LunchConstraint": True,
    "ResourceCriteriaConstraint": True,
}

CONSTRAINT_TAG = "autoscheduler_constraint_overrides"

# Descriptions for each constraint. Dict mapping from constraint name to short
# description
CONSTRAINT_DESCRIPTIONS = {
    "ContiguousConstraint": "Schedule sections over contiguous timeblocks.",
    "LunchConstraint": "Don't schedule multi-hour sections over lunch.",
    "PreconditionConstraint":
        "Only unschedule already-scheduled classes, etc.",
    "ResourceCriteriaConstraint":
        "Specially specified resource criteria must be met.",
    "RoomAvailabilityConstraint":
        "Only schedule classes in rooms that we have reserved.",
    "RoomConcurrencyConstraint":
        "Don't double-book rooms.",
    "SectionDurationConstraint": "Schedule sections for their duration.",
    "TeacherAvailabilityConstraint":
        "Teachers can only teach when they're available.",
    "TeacherConcurrencyConstraint":
        "Teachers can't teach two classes at once."
}


"""*******************Scoring**********************"""

# Default scorer names and weights for scorers. Format is:
#     ScorerClassName: weight
# This will be overridden by a tag, and then by user input. To not use a
# scorer, set its weight to 0. Note that in addition to these weights, each
# scorer has a scaling so that each 'relevant' section has weight
# 1/num_sections. See the docstring at the top of scoring.py for details. These
# weights therefore impose a loose per-section importance ranking on the
# scorers.
DEFAULT_SCORER_WEIGHTS = {
        "AdminDistributionScorer": 70.0,
        "CategoryBalanceScorer": 10.0,
        "LunchStudentClassHoursScorer": 20.0,
        "HungryTeacherScorer": 70.0,
        "NumSectionsScorer": 100.0,
        "NumSubjectsScorer": 60.0,
        "NumTeachersScorer": 50.0,
        "ResourceCriteriaScorer": 300.0,
        "ResourceMatchingScorer": 500.0,
        "ResourceValueMatchingScorer": 450.0,
        "RoomConsecutivityScorer": 10.0,
        "RoomSizeMismatchScorer": 350.0,
        "StudentClassHoursScorer": 50.0,
        "TeachersWhoLikeRunningScorer": 10.0
}

SCORER_TAG = "autoscheduler_scorer_weight_overrides"

# Dict mapping from scorer class name to short description.
SCORER_DESCRIPTIONS = {
    "AdminDistributionScorer":
        "Schedule admin classes evenly and not in the morning.",
    "CategoryBalanceScorer":
        "Schedule each category's student-class-hours evenly.",
    "LunchStudentClassHoursScorer":
        "Prioritize scheduling classes away from lunchtime.",
    "HungryTeacherScorer":
        "Avoid teachers teaching both blocks of lunch.",
    "NumSectionsScorer":
        "Schedule as many class sections as possible.",
    "NumSubjectsScorer":
        "Schedule as many distinct classes as possible.",
    "NumTeachersScorer":
        "Schedule as many distinct teachers' classes as possible.",
    "ResourceCriteriaScorer":
        "If we have specially defined resource criteria, score them.",
    "ResourceMatchingScorer":
        "If a section requested a resource, give it to them.",
    "ResourceValueMatchingScorer":
        "If a section requested a resource and value, do it.",
    "RoomConsecutivityScorer":
        "Try to schedule classes consecutively in rooms.",
    "RoomSizeMismatchScorer":
        "Schedule classes in appropriately sized rooms.",
    "StudentClassHoursScorer":
        "Schedule as many student-class-hours as possible.",
    "TeachersWhoLikeRunningScorer":
        "Avoid teachers teaching back-to-back in different rooms.",
}


"""********************Resources********************"""

# Default ResourceCriteria used for constraints. Format is:
#     name: specification
# See resource_checker.ResourceCriterion for details on the specification. The
# name is for overriding purposes, i.e. to override a particular criterion,
# create another with the same name in an override dict. To delete a criterion
# in an override, use None (either None or 'None' is okay) for the
# specification.
DEFAULT_RESOURCE_CONSTRAINTS = {
    # If you don't want to use a classroom, mark its name with a star.
    "restrict_star_classrooms":
        "if any section then not classroom matches {}".format(
            r"^\*.*$"),
    "restrict_star_classrooms_comment":
        "Ignore all classrooms with names marked with a star, e.g. *16-628.",
}

# Create a tag containing a JSON dict with this key to the relevant program.
# To leave comments, create an entry with "_comment" in the name, e.g.
# "sample_item_comment" with the comment in the value. The key should be the
# name of the resource criterion, and the value should be a criterion
# specification.  See resource_checker.ResourceCriterion for details.
RESOURCE_CONSTRAINTS_TAG = "autoscheduler_resource_constraint_overrides"

# Default ResourceCriteria used for scoring. Format is:
#     name: [specification, weight]
# See the comment on DEFAULT_RESOURCE_CONSTRAINTS for more details. Weights are
# all relative, and the total weight will be determined by the total weight of
# the ResourceCriteriaScorer.
DEFAULT_RESOURCE_SCORING = {
    # Nothing here, since ResourceMatchingScorer and
    # ResourceValueMatchingScorer should cover generic cases.
}

# See the instructions for RESOURCE_CONSTRAINTS_TAG.
RESOURCE_SCORING_TAG = "autoscheduler_resource_scoring_overrides"


# Whether or not to use the timer in util.py. If not, code will be somewhat
# faster.
USE_TIMER = False
