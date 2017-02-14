"""A Scorer can score a schedule, or (for performance reasons) predict the
change in score a particular schedule hypothetical schedule manipulation would
cause. Since some of these scorers are fairly global, e.g. depend on a
distribution, scorers are allowed to maintain an internal state; so a scorer
can initialize (or re-initialize) to a schedule, score the schedule it is
currently set to, predict a score for a hypothetical change (without changing
its state), or perform a change (i.e. updating its state).

A Scorer is expected to return a score in the range [0, 1].
"""
# TODO documentation on adding scorers


class BaseScorer:
    """Abstract class for scorers."""
    def __init__(self, schedule):
        """Initialize the scorer to the specified schedule."""
        self.update_schedule(schedule)

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        raise NotImplementedError

    def score_schedule_section(self, section, start_roomslot):
        """Returns a score in the range [0, 1] if the schedule currently
        reflected in internal state schedules the specified section starting at
        the specified roomslot."""
        raise NotImplementedError

    def score_move_section(self, section, start_roomslot):
        """Returns a score in the range [0, 1] if the schedule currently
        reflected in internal state moves the specified already-scheduled
        section to start at the specified roomslot."""
        raise NotImplementedError

    def score_unschedule_section(self, section):
        """Returns a score in the range [0, 1] if the schedule currently
        reflected in internal state unschedules the specified section."""
        raise NotImplementedError

    def score_swap_sections(self, section1, section2):
        """Returns a score in the range [0, 1] if the schedule currently
        reflected in internal state swaps the two specified already-scheduled
        sections."""
        raise NotImplementedError

    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        raise NotImplementedError

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        raise NotImplementedError

    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        raise NotImplementedError

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        raise NotImplementedError

    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        raise NotImplementedError


class CompositeScorer(BaseScorer):
    """A scorer which checks all the scorers you actually want, and weights them
    according to pre-specified weights."""
    def __init__(self, scorer_names_and_weights, schedule):
        """Takes in a list of pairs of scorer names (as strings) and weights (as
        floats), and loads them, initializing them to the specified schedule.
        All weights should be positive."""
        self.scorers_and_weights = []
        self.total_weight = 0.0
        available_scorers = globals()
        for scorer, weight in scorer_names_and_weights:
            assert weight > 0, "Scorer weights should be positive"
            print("Using scorer {}".format(scorer))
            self.scorers_and_weights.append(
                (available_scorers[scorer](schedule), weight))
            self.total_weight.append(weight)

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        total_score = 0.0
        for scorer, weight in self.scorers_and_weights:
            total_score += scorer.score_schedule() * weight
        return total_score / self.total_weight

    def score_schedule_section(self, section, start_roomslot):
        """Returns a score in the range [0, 1] if the schedule currently
        reflected in internal state schedules the specified section starting at
        the specified roomslot."""
        total_score = 0.0
        for scorer, weight in self.scorers_and_weights:
            total_score += \
                scorer.score_schedule_section(section, start_roomslot) * weight
        return total_score / self.total_weight

    def score_move_section(self, section, start_roomslot):
        """Returns a score in the range [0, 1] if the schedule currently
        reflected in internal state moves the specified already-scheduled
        section to start at the specified roomslot."""
        total_score = 0.0
        for scorer, weight in self.scorers_and_weights:
            total_score += \
                scorer.score_move_section(section, start_roomslot) * weight
        return total_score / self.total_weight

    def score_unschedule_section(self, section):
        """Returns a score in the range [0, 1] if the schedule currently
        reflected in internal state unschedules the specified section."""
        total_score = 0.0
        for scorer, weight in self.scorers_and_weights:
            total_score += \
                scorer.score_unschedule_section(section) * weight
        return total_score / self.total_weight

    def score_swap_sections(self, section1, section2):
        """Returns a score in the range [0, 1] if the schedule currently
        reflected in internal state swaps the two specified already-scheduled
        sections."""
        total_score = 0.0
        for scorer, weight in self.scorers_and_weights:
            total_score += \
                scorer.score_swap_sections(section1, section2) * weight
        return total_score / self.total_weight

    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_schedule(schedule)

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_schedule_section(section, start_roomslot)

    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_move_section(section, start_roomslot)

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_unschedule_section(section)

    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_swap_sections(section1, section2)


class AdminDistributionScorer(BaseScorer):
    """Admins' classes should be spread out over the day, and minimally in the
    mornings."""
    pass


class CategoryBalanceScorer(BaseScorer):
    """Each category should have its student-capacity spread out evenly over
    the timeblocks in each day."""
    pass


class LunchStudentClassHoursScorer(BaseScorer):
    """Preferentially schedule student-class-hours during non-lunch blocks,
    assuming (some fraction of) students are required to have lunch during
    those times so there will be less demand."""

    # Make sure this accounts for room capacities

    pass


class HungryTeacherScorer(BaseScorer):
    """Avoid teachers having to teach during both blocks of lunch."""
    pass


class NumSectionsScorer(BaseScorer):
    """Schedule as many sections as possible."""
    pass


class NumSubjectsScorer(BaseScorer):
    """Schedule as many unique classes (i.e. subjects) as possible."""
    pass


class NumTeachersScorer(BaseScorer):
    """Schedule as many distinct teachers' classes as possible."""
    pass


class ResourceCriterionScorer(BaseScorer):
    """Match ResourceCriteria (according to given weights) as well as
    possible."""
    pass


class ResourceMovementScorer(BaseScorer):
    """Try to group unmatched ResourceCriteria into consecutive timeblocks in
    the same classroom, e.g. to minimize having to move projectors between
    classrooms."""
    pass


class RoomConsecutivityScorer(BaseScorer):
    """Try to schedule classes consecutively in classrooms. This is a good
    heuristic for being able to schedule long classes later, as well as for
    minimizing having to repeatedly clean or lock/unlock rooms."""
    pass


class RoomSizeMismatchScorer(BaseScorer):
    """Match room sizes to classes as much as possible."""
    # Make sure this doesn't get really sad trying to schedule a 200-capacity
    # class in 26-100, or a 600-capacity class in 1-190
    pass


class StudentClassHoursScorer(BaseScorer):
    """Schedule as many student-class-hours as possible."""
    # Make sure this accounts for room capacities
    pass


class TeachersWhoLikeRunningScorer(BaseScorer):
    """Minimize teachers teaching back-to-back classes in different
    locations."""
    pass


class TiredTeacherScorer(BaseScorer):
    """Avoid teachers teaching too many back-to-back classes in a row."""
    # Make sure this doesn't prevent teachers from teaching a full schedule.
    pass
