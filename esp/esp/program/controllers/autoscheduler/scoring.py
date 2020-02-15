"""Classes for judging how good a schedule is.

TO ADD NEW SCORERS:
Extend and implement BaseScorer, and update config.py with a description and
default weight. Set self.scaling for your scorer as appropriate (see below).

A Scorer stores internal state representing the relevant information of a
schedule, and can return its current score, update its state with a fresh
schedule, or update its state due to a schedule/unschedule/move/swap
manipulation.

We use this design because scorers tend to describe global state (e.g. "how
many sections are scheduled?") and would need to read the entire schedule to
produce a score for each schedule manipulation, which would be very slow.
However, individual schedule manipulations often do not require drastic state
changes. Thus, scorers are expected to be fast at returning its current score
or updating its state due to an individual manipulation, but not necessarily
fast at loading a fresh schedule.

A Scorer is expected to return a score in the range [0, 1], where 1 is good and
0 is bad. Each Scorer is also expected to keep a 'scaling' attribute, e.g.
initialized in update_schedule(), so that when its score is multiplied by the
scaling attribute, any given section will (in general) have an impact of
approximately at most 1 / num_sections. Note this is maximum impact, not
expected impact, though in some cases we might not care about the difference.
The logic is: if I'm scheduling a section, how much does this evaluation decide
whether I want to schedule it (assuming the evaluation is relevant)?  (For
example, AdminDistributionScorer will be impacted only by sections with admins
teaching, so we need to scale down.) This allows scorer weights to be
determined by relative importance to scheduling a section without accounting
for this sort of behavior."""

import logging

import esp.program.controllers.autoscheduler.util as util

logger = logging.getLogger(__name__)


class BaseScorer(object):
    """Abstract class for scorers."""
    def __init__(self, schedule, **kwargs):
        """Initialize the scorer to the specified schedule."""
        self.scaling = 1.0  # default
        self.update_schedule(schedule)

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
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
        already-scheduled section to start at the specified roomslot.

        We provide a default implementation here, but note that this is not
        always an accurate implementation because the call to
        update_schedule_section will be called without actually having
        unscheduled the relevant section yet. RoomConsecutivityScorer is an
        example of such a scorer for which this matters, but generally speaking
        it only matters if the scorer looks at other classes to update the
        score."""
        self.update_unschedule_section(section)
        self.update_schedule_section(section, start_roomslot)

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        raise NotImplementedError

    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections. See the note on update_move_section regarding this
        default implementation."""
        self.update_move_section(section1, section2.assigned_roomslots[0])
        self.update_move_section(section2, section1.assigned_roomslots[0])


class CompositeScorer(BaseScorer):
    """A scorer which checks all the scorers you actually want, and weights them
    according to pre-specified weights."""
    def __init__(self, scorer_names_and_weights, schedule, **kwargs):
        """Takes in a dict of scorer names (as strings) mapping to weights (as
        floats), and loads them, initializing them to the specified schedule.
        All weights should be positive."""
        self.verbose = kwargs.get("verbose", False)
        self.scorers_and_weights = []
        if len(scorer_names_and_weights) == 0:
            # If we didn't receive any names and weights, we are a trivial
            # scorer. Set total weight to 1 to avoid division by 0.
            self.total_weight = 1.0
        else:
            self.total_weight = 0.0
            available_scorers = globals()
            for scorer, weight in scorer_names_and_weights.iteritems():
                if weight is None or weight == 0:
                    continue
                assert weight >= 0, "Scorer weights should be nonnegative"
                logger.info("Using scorer {}".format(scorer))
                scorer_obj = available_scorers[scorer](schedule, **kwargs)
                self.scorers_and_weights.append((scorer_obj, weight))
        self.compute_total_weight()

    def compute_total_weight(self):
        """Updates the value of total_weight. Each Scorer is weighted by its
        scaling factor times the user-specified weight."""
        self.total_weight = 0.0
        for scorer, weight in self.scorers_and_weights:
            self.total_weight += scorer.scaling * weight
        if self.total_weight == 0:
            self.total_weight = 1.0

    @util.timed_func("CompositeScorer_score_schedule")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state. This should be implemented efficiently so it can be
        called frequently."""
        total_score = 0.0
        for scorer, weight in self.scorers_and_weights:
            score = scorer.score_schedule()
            if self.verbose:
                logger.info("Scorer {} has score {}".format(
                        scorer.__class__.__name__, score))
            total_score += score * weight * scorer.scaling
        return total_score / self.total_weight

    def get_all_score_schedule(self):
        """Returns the scores from each component scorer in alphabetical order
        by scorer name."""
        scores = [(scorer.__class__.__name__, weight, scorer.score_schedule())
                  for scorer, weight in self.scorers_and_weights]
        return (sorted(scores, key=lambda x: x[0]), self.score_schedule())

    @util.timed_func("CompositeScorer_update_schedule")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_schedule(schedule)
        self.compute_total_weight()

    @util.timed_func("CompositeScorer_update_schedule_section")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_schedule_section(section, start_roomslot)

    @util.timed_func("CompositeScorer_update_move_section")
    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_move_section(section, start_roomslot)

    @util.timed_func("CompositeScorer_update_unschedule_section")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_unschedule_section(section)

    @util.timed_func("CompositeScorer_update_swap_section")
    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        for scorer, weight in self.scorers_and_weights:
            scorer.update_swap_sections(section1, section2)


class AdminDistributionScorer(BaseScorer):
    """Admins' classes should be spread out over the day, and minimally in the
    mornings."""
    @util.timed_func("admindistributionscorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # We do a simple linear penalty: for each timeslot, if the proportion
        # of admins teaching in each timeslot exceeds the ideal distribution by
        # x, contribute x to the penalty. Cap the penalty at 1.
        self.penalty = 0.0
        for t in self.ideal_distribution_dict:
            ideal = self.ideal_distribution_dict[t]
            actual = self.admins_per_timeslot[t] / self.total_admins
            if actual > ideal:
                self.penalty += actual - ideal
        return max(0.0, 1 - self.penalty)

    @util.timed_func("admindistributionscorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # The ideal distribution indicates what fraction of all admins should
        # be teaching during each timeslot. We approximate the ideal
        # distribution saying that at most 1/3 of all admins should be teaching
        # during any given timeslot, and no admins should teach in first
        # timeslot each day.
        ideal_distribution = [0.0]
        prev_timeslot = schedule.timeslots[0]
        for t in schedule.timeslots[1:]:
            if t.start.day == prev_timeslot.start.day:
                ideal_distribution.append(1/3.0)
            else:
                ideal_distribution.append(0.0)
            prev_timeslot = t
        self.ideal_distribution_dict = {}
        for x, ts in zip(ideal_distribution, schedule.timeslots):
            self.ideal_distribution_dict[ts.id] = x
        self.total_admins = float(sum(
            [t.is_admin for t in schedule.teachers.itervalues()]))
        self.admins_per_timeslot = {t.id: 0.0 for t in schedule.timeslots}
        for section in schedule.class_sections.itervalues():
            for teacher in section.teachers:
                if teacher.is_admin:
                    for roomslot in section.assigned_roomslots:
                        self.admins_per_timeslot[roomslot.timeslot.id] += 1
        # Each section's can have impact up to its duration times the number of
        # admins teaching, divided by the number of admins.
        # So we divide by:
        #     average duration
        #     average teacher count
        #     number of sections
        # and multiply by number of admins. This is technically wrong if
        # timeblocks aren't one hour long, but whatever.
        average_duration = 0.0
        average_num_teachers = 0.0
        for section in schedule.class_sections.itervalues():
            average_duration += section.duration
            average_num_teachers += len(section.teachers)
        num_sections = len(schedule.class_sections)
        average_duration /= num_sections
        average_num_teachers /= num_sections
        self.scaling = self.total_admins / (
            average_duration * average_num_teachers * num_sections)

    @util.timed_func("admindistributionscorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        for teacher in section.teachers:
            if teacher.is_admin:
                for roomslot in roomslots:
                    self.admins_per_timeslot[roomslot.timeslot.id] += 1

    @util.timed_func("admindistributionscorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        for teacher in section.teachers:
            if teacher.is_admin:
                for roomslot in section.assigned_roomslots:
                    self.admins_per_timeslot[roomslot.timeslot.id] -= 1


class CategoryBalanceScorer(BaseScorer):
    """Each category should have its student-capacity spread out evenly over
    the timeblocks in each day."""

    @util.timed_func("categorybalancescorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # For each category, track a penalty; for each timeslot, if the
        # fraction of total student_class_hours in that category (computed as
        # capacity times timeslot duration divided by total student-class-hours
        # for that category) exceeds one over the number of timeslots, add this
        # excess (as a decimal) to the penalty. Average this penalty over all
        # categories. Note that this gives some slack because total
        # student-class-hours includes time between two timeslots in multi-hour
        # classes.
        total_penalty = 0.0
        for category, student_class_hours in \
                self.student_class_hours_by_category.iteritems():
            capacity_per_timeslot = \
                self.capacity_per_timeslot_by_category[category]
            leeway = 1.0 / len(capacity_per_timeslot)
            for timeslot, capacity in capacity_per_timeslot.iteritems():
                duration = self.timeslot_durations[timeslot]
                fractional_capacity = \
                    capacity * duration / student_class_hours
                if fractional_capacity > leeway:
                    total_penalty += capacity / student_class_hours - leeway
        return 1 - (total_penalty / len(self.student_class_hours_by_category))

    @util.timed_func("categorybalancescorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # Each section has impact proportional to its student-class-hours,
        # which is probably fine if we just leave it at 1 since we probably do
        # want large sections to care more about this..
        self.timeslot_durations = {
                t.id: t.duration for t in schedule.timeslots}
        self.student_class_hours_by_category = {}
        for sec in schedule.class_sections.itervalues():
            self.student_class_hours_by_category[sec.category] = \
                self.student_class_hours_by_category.get(sec.category, 0.0) \
                + sec.capacity * sec.duration
        self.capacity_per_timeslot_by_category = {
            c: {t.id: 0.0 for t in schedule.timeslots} for c in
            self.student_class_hours_by_category}
        for section in schedule.class_sections.itervalues():
            capacity_per_timeslot = self.capacity_per_timeslot_by_category[
                section.category]
            for roomslot in section.assigned_roomslots:
                actual_capacity = min(section.capacity, roomslot.room.capacity)
                capacity_per_timeslot[roomslot.timeslot.id] += actual_capacity

    @util.timed_func("categorybalancescorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        for roomslot in roomslots:
            actual_capacity = min(section.capacity, roomslot.room.capacity)
            self.capacity_per_timeslot_by_category[section.category][
                roomslot.timeslot.id] += actual_capacity

    @util.timed_func("categorybalancescorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        for roomslot in section.assigned_roomslots:
            actual_capacity = min(section.capacity, roomslot.room.capacity)
            self.capacity_per_timeslot_by_category[section.category][
                roomslot.timeslot.id] -= actual_capacity


class LunchStudentClassHoursScorer(BaseScorer):
    """Preferentially schedule student-class-hours during non-lunch blocks,
    assuming (some fraction of) students are required to have lunch during
    those times so there will be less demand."""

    @util.timed_func("lunchstudentclasshoursscorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # We return simply the fraction of all possible student-class-hours
        # which are scheduled during non-lunch timeslots. Note that this is an
        # underestimate because the denominator accounts for time between
        # timeslots in multi-hour classes, and the numerator does not.
        return self.non_lunch_student_class_hours / \
            self.total_student_class_hours

    @util.timed_func("lunchstudentclasshoursscorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # Each section has impact proportional to its student-class-hours,
        # which is probably fine if we just leave it at 1 since we probably do
        # want large sections to care more about this..

        self.lunch_timeslots = set()
        for timeslots in schedule.lunch_timeslots.itervalues():
            self.lunch_timeslots.update([t.id for t in timeslots])
        self.total_student_class_hours = float(sum(
            [sec.capacity * sec.duration for sec in
             schedule.class_sections.itervalues()]))
        self.non_lunch_student_class_hours = 0.0
        for section in schedule.class_sections.itervalues():
            for roomslot in section.assigned_roomslots:
                actual_capacity = min(section.capacity, roomslot.room.capacity)
                if roomslot.timeslot.id not in self.lunch_timeslots:
                    self.non_lunch_student_class_hours += \
                        actual_capacity * roomslot.timeslot.duration

    @util.timed_func("lunchstudentclasshoursscorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        for roomslot in roomslots:
            actual_capacity = min(section.capacity, roomslot.room.capacity)
            if roomslot.timeslot.id not in self.lunch_timeslots:
                self.non_lunch_student_class_hours += \
                    actual_capacity * roomslot.timeslot.duration

    @util.timed_func("lunchstudentclasshoursscorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        for roomslot in section.assigned_roomslots:
            actual_capacity = min(section.capacity, roomslot.room.capacity)
            if roomslot.timeslot.id not in self.lunch_timeslots:
                self.non_lunch_student_class_hours -= \
                    actual_capacity * roomslot.timeslot.duration


class HungryTeacherScorer(BaseScorer):
    """Avoid teachers having to teach during both blocks of lunch."""

    @util.timed_func("hungryteacherscorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the total fraction of non-hungry teachers.
        return 1 - len(self.hungry_teachers) / self.total_teachers

    @util.timed_func("hungryteacherscorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        self.total_teachers = float(len(schedule.teachers))
        lunch_timeslots = []
        for timeslots in schedule.lunch_timeslots.itervalues():
            lunch_timeslots += timeslots
        self.lunch_timeslots = schedule.lunch_timeslots
        # Dict of whether the teachers are teaching in each lunch timeslot.
        self.lunch_timeslots_by_teacher = {
            teacher_id: {timeslot.id: False for timeslot in lunch_timeslots}
            for teacher_id in schedule.teachers}
        for section in schedule.class_sections.itervalues():
            for teacher in section.teachers:
                lunch_timeslots_teaching = self.lunch_timeslots_by_teacher[
                    teacher.id]
                for roomslot in section.assigned_roomslots:
                    if roomslot.timeslot.id in lunch_timeslots_teaching:
                        lunch_timeslots_teaching[roomslot.timeslot.id] = True
        self.hungry_teachers = set()
        for t in self.lunch_timeslots_by_teacher:
            self.update_teacher_hungriness(t)
        # Each section can have impact equal to the number of teachers in it,
        # divided by the total number of teachers.
        num_section_teachers = 0.0
        for section in schedule.class_sections.itervalues():
            num_section_teachers += len(section.teachers)
        self.scaling = self.total_teachers / num_section_teachers

    @util.timed_func("hungryteacherscorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        for teacher in section.teachers:
            lunch_timeslots_teaching = self.lunch_timeslots_by_teacher[
                teacher.id]
            for roomslot in roomslots:
                if roomslot.timeslot.id in lunch_timeslots_teaching:
                    lunch_timeslots_teaching[roomslot.timeslot.id] = True
            self.update_teacher_hungriness(teacher.id)

    @util.timed_func("hungryteacherscorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        for teacher in section.teachers:
            lunch_timeslots_teaching = self.lunch_timeslots_by_teacher[
                teacher.id]
            for roomslot in section.assigned_roomslots:
                if roomslot.timeslot.id in lunch_timeslots_teaching:
                    lunch_timeslots_teaching[roomslot.timeslot.id] = False
            self.update_teacher_hungriness(teacher.id)

    def update_teacher_hungriness(self, teacher_id):
        """Update the teacher's membership in self.hungry_teachers."""
        timeslots_teaching = self.lunch_timeslots_by_teacher[teacher_id]
        for timeslots in self.lunch_timeslots.itervalues():
            if all([timeslots_teaching[t.id] for t in timeslots]):
                self.hungry_teachers.add(teacher_id)
                return
        if teacher_id in self.hungry_teachers:
            self.hungry_teachers.remove(teacher_id)


class NumSectionsScorer(BaseScorer):
    """Schedule as many sections as possible."""

    @util.timed_func("numsectionsscorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the fraction of sections which are scheduled.
        return self.scheduled_sections / self.total_sections

    @util.timed_func("numsectionsscorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # The scaling is trivially 1.
        self.total_sections = float(len(schedule.class_sections))
        self.scheduled_sections = sum(
            [s.is_scheduled() for s in schedule.class_sections.itervalues()])

    @util.timed_func("numsectionsscorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        self.scheduled_sections += 1

    @util.timed_func("numsectionsscorer")
    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        pass

    @util.timed_func("numsectionsscorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        assert self.scheduled_sections > 0
        self.scheduled_sections -= 1

    @util.timed_func("numsectionsscorer")
    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        pass


class NumSubjectsScorer(BaseScorer):
    """Schedule as many unique classes (i.e. subjects) as possible."""

    @util.timed_func("NumSubjectsScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the fraction of subjects which are scheduled.
        return self.scheduled_subjects / self.total_subjects

    @util.timed_func("NumSubjectsScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        subjects = set(
            [s.parent_class for s in schedule.class_sections.itervalues()])
        self.total_subjects = float(len(subjects))
        self.num_scheduled_sections_by_subject = {s: 0 for s in subjects}
        for section in schedule.class_sections.itervalues():
            if section.is_scheduled():
                self.num_scheduled_sections_by_subject[
                    section.parent_class] += 1
        self.scheduled_subjects = sum(
            [(num_sections > 0) for num_sections in
                self.num_scheduled_sections_by_subject.itervalues()])
        self.scaling = self.total_subjects / len(schedule.class_sections)

    @util.timed_func("NumSubjectsScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        self.num_scheduled_sections_by_subject[section.parent_class] += 1
        if self.num_scheduled_sections_by_subject[section.parent_class] == 1:
            self.scheduled_subjects += 1

    @util.timed_func("NumSubjectsScorer")
    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        pass

    @util.timed_func("NumSubjectsScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        assert self.num_scheduled_sections_by_subject[section.parent_class] > 0
        self.num_scheduled_sections_by_subject[section.parent_class] -= 1
        if self.num_scheduled_sections_by_subject[section.parent_class] == 0:
            self.scheduled_subjects -= 1

    @util.timed_func("NumSubjectsScorer")
    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        pass


class NumTeachersScorer(BaseScorer):
    """Schedule as many distinct teachers' classes as possible."""

    @util.timed_func("NumTeachersScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the fraction of teachers which have scheduled classes.
        return self.scheduled_teachers / self.total_teachers

    @util.timed_func("NumTeachersScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        self.total_teachers = float(len(schedule.teachers))
        self.num_scheduled_sections_by_teacher = \
            {t: 0 for t in schedule.teachers}
        for section in schedule.class_sections.itervalues():
            if section.is_scheduled():
                for t in section.teachers:
                    self.num_scheduled_sections_by_teacher[t.id] += 1
        self.scheduled_teachers = sum(
            [(num_sections > 0) for num_sections in
                self.num_scheduled_sections_by_teacher.itervalues()])
        self.scaling = self.total_teachers / len(schedule.class_sections)

    @util.timed_func("NumTeachersScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        for t in section.teachers:
            self.num_scheduled_sections_by_teacher[t.id] += 1
            if self.num_scheduled_sections_by_teacher[t.id] == 1:
                self.scheduled_teachers += 1

    @util.timed_func("NumTeachersScorer")
    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        pass

    @util.timed_func("NumTeachersScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        for t in section.teachers:
            assert self.num_scheduled_sections_by_teacher[t.id] > 0
            self.num_scheduled_sections_by_teacher[t.id] -= 1
            if self.num_scheduled_sections_by_teacher[t.id] == 0:
                self.scheduled_teachers -= 1

    @util.timed_func("NumTeachersScorer")
    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        pass


class ResourceCriteriaScorer(BaseScorer):
    """Match ResourceCriteria (according to given weights) as well as
    possible."""

    def __init__(self, schedule, **kwargs):
        """Initialize the scorer to the specified schedule, with the given
        ResourceCriteria. kwargs should contain the key resource_criteria,
        which is a list of pairs of ResourceCriterions and weights."""
        # Resource criteria needs to be loaded before super() is called, or
        # else update_schedule won't have resource criteria to refer to.
        self.resource_criteria = kwargs.get("resource_criteria", [])
        super(ResourceCriteriaScorer, self).__init__(schedule, **kwargs)
        # We want to avoid the situation where adding more ResourceCriteria
        # dilutes existing ones; at the same time, we want to avoid the
        # situation where adding low-weight ResourceCriteria makes high-weight
        # overweighted. So we scale so that the highest-weight
        # ResourceCriterion has weight 1. Yes, this means we're scaling up.
        if len(self.resource_criteria) == 0:
            self.scaling = 1.0
        else:
            max_weight = max([
                weight for criterion, weight in self.resource_criteria])
            self.scaling = self.total_weight / max_weight

    @util.timed_func("ResourceCriteriaScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the average score, averaged across all sections. Each score is
        # the weighted average (over all resource criteria) of 1 if the
        # criterion is met, 0 if not. If the section isn't scheduled, score
        # is 0.
        return self.total_score / (self.total_weight * self.num_sections)

    def process_section(self, section, room):
        """Computes the score for a given section assigned to the given
        room."""
        output = 0.0
        for resource_criterion, weight in self.resource_criteria:
            if resource_criterion.check_match(section, room):
                output += weight
        return output

    @util.timed_func("ResourceCriteriaScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # See constructor for scaling.
        self.total_weight = float(sum(
            [weight for criterion, weight in self.resource_criteria]))
        if self.total_weight == 0:
            self.total_weight = 1  # Avoid division by 0
        self.num_sections = len(schedule.class_sections)
        self.total_score = 0.0
        for section in schedule.class_sections.itervalues():
            if section.is_scheduled():
                self.total_score += self.process_section(
                    section, section.assigned_roomslots[0].room)

    @util.timed_func("ResourceCriteriaScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        self.total_score += self.process_section(section, start_roomslot.room)

    @util.timed_func("ResourceCriteriaScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        self.total_score -= self.process_section(
            section, section.assigned_roomslots[0].room)


class ResourceMatchingScorer(BaseScorer):
    """If a section asks for a resource, try to satisfy this request."""

    @util.timed_func("ResourceMatchingScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the average fraction of matches over all sections. Unscheduled
        # sections are counted as no matches.
        return self.total_score / self.num_sections

    def process_section(self, section, room):
        """Computes the score for a given section assigned to the given
        room."""
        # Return the fraction of satisfied resource requests.
        if len(section.resource_requests) == 0:
            return 1.0
        met_criteria = 0.0
        for restype_name in section.resource_requests:
            if restype_name in room.furnishings:
                met_criteria += 1
        return met_criteria / len(section.resource_requests)

    @util.timed_func("ResourceMatchingScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # Scaling is just the default 1 because we're just scoring by section.
        self.num_sections = len(schedule.class_sections)
        self.total_score = 0.0
        for section in schedule.class_sections.itervalues():
            if section.is_scheduled():
                self.total_score += self.process_section(
                    section, section.assigned_roomslots[0].room)

    @util.timed_func("ResourceMatchingScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        self.total_score += self.process_section(section, start_roomslot.room)

    @util.timed_func("ResourceMatchingScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        self.total_score -= self.process_section(
            section, section.assigned_roomslots[0].room)


# I don't feel like implementing this right now :(
# class ResourceMovementScorer(BaseScorer):
#     """Try to group unmatched ResourceCriteria into consecutive timeblocks in
#     the same classroom, e.g. to minimize having to move projectors between
#     classrooms."""
#     pass


class ResourceValueMatchingScorer(BaseScorer):
    """If a section asks for a resource with a specific value, try to satisfy
    this request. If all classrooms have the same value for a resource type,
    ignore that resource for this purpose."""

    @util.timed_func("ResourceValueMatchingScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the average fraction of matches over all sections. Unscheduled
        # sections are counted as no matches.
        return self.total_score / self.num_sections

    def process_section(self, section, room):
        """Computes the score for a given section assigned to the given
        room."""
        # Return the fraction of satisfied resource requests.
        met_criteria = 0.0
        requested_criteria = 0.0
        for request in section.resource_requests.itervalues():
            if request.name not in self.requests_to_ignore \
                    and request.value != "":
                requested_criteria += 1
                if request.name in room.furnishings \
                        and room.furnishings[request.name].value \
                        == request.value:
                    met_criteria += 1
        if requested_criteria == 0.0:
            return 1.0
        else:
            return met_criteria / requested_criteria

    @util.timed_func("ResourceValueMatchingScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # Scaling is just the default 1 because we're just scoring by section.
        self.num_sections = len(schedule.class_sections)

        furnishing_values = {}
        for room in schedule.classrooms.itervalues():
            for furnishing in room.furnishings.itervalues():
                if furnishing.name not in furnishing_values:
                    furnishing_values[furnishing.name] = set()
                furnishing_values[furnishing.name].add(furnishing.value)
        self.requests_to_ignore = set()
        for name, values in furnishing_values.iteritems():
            if len(values) == 1:
                self.requests_to_ignore.add(name)
        self.total_score = 0.0
        for section in schedule.class_sections.itervalues():
            if section.is_scheduled():
                self.total_score += self.process_section(
                    section, section.assigned_roomslots[0].room)

    @util.timed_func("ResourceValueMatchingScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        self.total_score += self.process_section(section, start_roomslot.room)

    @util.timed_func("ResourceValueMatchingScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        self.total_score -= self.process_section(
            section, section.assigned_roomslots[0].room)


class RoomConsecutivityScorer(BaseScorer):
    """Try to schedule classes consecutively in classrooms. This is a good
    heuristic for being able to schedule long classes later, as well as for
    minimizing having to repeatedly clean or lock/unlock rooms."""

    def boundary_complete_before(self, roomslot, ignore_section=None):
        """The boundary-before after a roomslot is complete if either there's
        no roomslot before or there's another class scheduled before it."""

        room = roomslot.room
        start_idx = roomslot.index()
        if start_idx > 0:
            prev_roomslot = room.availability[start_idx - 1]
            return (prev_roomslot.assigned_section is not None
                    and prev_roomslot.assigned_section != ignore_section) \
                or not util.contiguous(
                    prev_roomslot.timeslot, roomslot.timeslot)
        else:
            return True

    def boundary_complete_after(self, roomslot, ignore_section=None,
                                avoid_doublecount=False):
        """The boundary-after a roomslit is complete if either there's no
        roomslot after or there's another class scheduled after it."""
        next_roomslot = roomslot.next()
        return next_roomslot is None \
            or (not avoid_doublecount
                and next_roomslot.assigned_section is not None
                and next_roomslot.assigned_section != ignore_section) \
            or not util.contiguous(
                roomslot.timeslot, next_roomslot.timeslot)

    @util.timed_func("RoomConsecutivityScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""

        # Return the fraction of complete boundaries, i.e. start or end of a
        # section with either no timeslot before/after or another class
        # before/after in the room. (Equivalently, a boundary is incomplete iff
        # it's between two available and contiguous timeslots exactly one of
        # which has a section scheduled.) Boundaries between two sections are
        # not doublecounted, because this makes the computation slightly
        # easier. (TODO) This means that e.g. a classroom with two hours of
        # availability and two one-hour sections in it will only have 3 out of
        # 4 boundaries complete, which is not great. A better behavior would
        # probably be to count boundaries between sections once for each
        # section, but this makes updating the score upon section schedule
        # slightly harder to compute.
        return self.complete_boundaries / self.num_sections / 2.0

    @util.timed_func("RoomConsecutivityScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # Scaling is just the default 1 because we're just scoring by section.
        self.num_sections = float(len(schedule.class_sections))

        # A count of start or end of a section with either no timeslot
        # before/after or another room before/after. Boundaries between two
        # sections are not doublecounted.
        self.complete_boundaries = 0.0
        for section in schedule.class_sections.itervalues():
            if section.is_scheduled():
                if self.boundary_complete_before(
                        section.assigned_roomslots[0]):
                    self.complete_boundaries += 1
                if self.boundary_complete_after(
                        section.assigned_roomslots[-1],
                        avoid_doublecount=True):
                    self.complete_boundaries += 1

    @util.timed_func("RoomConsecutivityScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        if self.boundary_complete_before(start_roomslot):
            self.complete_boundaries += 1
        if self.boundary_complete_after(roomslots[-1]):
            self.complete_boundaries += 1

    @util.timed_func("RoomConsecutivityScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        roomslots = section.assigned_roomslots
        if self.boundary_complete_before(roomslots[0]):
            self.complete_boundaries -= 1
        if self.boundary_complete_after(roomslots[-1]):
            self.complete_boundaries -= 1

    @util.timed_func("RoomConsecutivityScorer")
    def update_move_section(self, section, start_roomslot):
        """The default update_move_section implementation is incorrect here
        because this function depends on the external schedule state."""
        roomslots = section.assigned_roomslots
        if self.boundary_complete_before(roomslots[0]):
            self.complete_boundaries -= 1
        if self.boundary_complete_after(roomslots[-1]):
            self.complete_boundaries -= 1
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        if self.boundary_complete_before(start_roomslot,
                                         ignore_section=section):
            self.complete_boundaries += 1
        if self.boundary_complete_after(roomslots[-1], ignore_section=section):
            self.complete_boundaries += 1

    @util.timed_func("RoomConsecutivityScorer")
    def update_swap_sections(self, section1, section2):
        pass


class RoomSizeMismatchScorer(BaseScorer):
    """Match room sizes to classes as much as possible."""
    def penalty_for_section_and_room(self, section, room):
        """
        For each section assigned to a room, we assign a penalty equal to the
        fraction that the larger capacity is greater than the lesser
        capacity, up to a maximum of 100%. For an unscheduled section, this
        penalty is 0. We square each penalty and average this over all
        sections."""

        section_capacity = min(self.max_room_size, section.capacity)
        room_capacity = min(self.max_class_size, room.capacity)
        numerator = max(section_capacity, room_capacity)
        denominator = min(section_capacity, room_capacity)
        if denominator == 0:
            # Something's wrong here, but let's just give the maximum
            # penalty instead of crashing.
            return 1.0
        else:
            return min(1.0, ((1.0 * numerator / denominator) - 1.0) ** 2)

    @util.timed_func("RoomSizeMismatchScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # See update_schedule for a description of how scoring works here.
        return 1.0 - self.total_penalty

    @util.timed_func("RoomSizeMismatchScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # To deal with huge rooms and classes, if any class is larger than the
        # largest room, we consider its capacity to just match that of the
        # largest room, and vice versa.

        # Scaling is the default 1 because we're already scoring per section.
        self.max_class_size = max(
            [s.capacity for s in schedule.class_sections.itervalues()])
        self.max_room_size = max(
            [c.capacity for c in schedule.classrooms.itervalues()])
        self.num_sections = float(len(schedule.class_sections))
        self.total_penalty = 0.0
        for section in schedule.class_sections.itervalues():
            if section.is_scheduled():
                room = section.assigned_roomslots[0].room
                penalty = self.penalty_for_section_and_room(section, room)
                self.total_penalty += penalty / self.num_sections

    @util.timed_func("RoomSizeMismatchScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        room = start_roomslot.room
        penalty = self.penalty_for_section_and_room(section, room)
        self.total_penalty += penalty / self.num_sections

    @util.timed_func("RoomSizeMismatchScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        room = section.assigned_roomslots[0].room
        penalty = self.penalty_for_section_and_room(section, room)
        self.total_penalty -= penalty / self.num_sections


class StudentClassHoursScorer(BaseScorer):
    """Schedule as many student-class-hours as possible."""

    def get_effective_student_class_hours(self, section, roomslot=None):
        """Compute the effective student-class-hours for a section, which is
        the capacity clamped by room size times duration. If no roomslot is
        provided, we use the section's first roomslot instead; if it doesn't
        exist, return 0."""

        if roomslot is None:
            if not section.is_scheduled():
                return 0.0
            else:
                roomslot = section.assigned_roomslots[0]
        room_capacity = roomslot.room.capacity
        actual_capacity = min(section.capacity, room_capacity)
        return actual_capacity * section.duration

    @util.timed_func("StudentClassHoursScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # We return simply the fraction of all possible student-class-hours
        # which are scheduled.
        return self.scheduled_student_class_hours / \
            self.total_student_class_hours

    @util.timed_func("StudentClassHoursScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # A section's impact is proportional to its student-class-hours, which
        # should be fine for leaving the scaling at 1.
        self.total_student_class_hours = float(sum(
            [sec.capacity * sec.duration for sec in
             schedule.class_sections.itervalues()]))
        self.scheduled_student_class_hours = sum(
            [self.get_effective_student_class_hours(sec)
             for sec in schedule.class_sections.itervalues()])

    @util.timed_func("StudentClassHoursScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        self.scheduled_student_class_hours += \
            self.get_effective_student_class_hours(section, start_roomslot)

    @util.timed_func("StudentClassHoursScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        self.scheduled_student_class_hours -= \
            self.get_effective_student_class_hours(section)


class TeachersWhoLikeRunningScorer(BaseScorer):
    """Minimize teachers teaching back-to-back classes in different
    locations."""
    @util.timed_func("TeachersWhoLikeRunningScorer")
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # We count the number of times anyone is teaching two consecutive
        # timeslots in different rooms, and divide by the number of total
        # sections.
        return 1.0 - self.running_count / self.num_sections

    @util.timed_func("TeachersWhoLikeRunningScorer")
    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # Since this is a per-section scorer, the scaling is left at 1.
        self.num_sections = float(len(schedule.class_sections))
        self.timeslot_indices = {
            t.id: i for i, t in enumerate(schedule.timeslots)}
        self.timeslots = schedule.timeslots
        # Maps from teacher IDs to dicts from timeslot IDs to roomslots.
        self.times_teacher_is_teaching = {
            teacher: {} for teacher in schedule.teachers}
        for section in schedule.class_sections.itervalues():
            for teacher in section.teachers:
                for roomslot in section.assigned_roomslots:
                    self.times_teacher_is_teaching[teacher.id][
                        roomslot.timeslot.id] = roomslot
        self.running_count = 0.0
        for teacher, times_teaching in \
                self.times_teacher_is_teaching.iteritems():
            for timeslot_id, roomslot in times_teaching.iteritems():
                timeslot_index = self.timeslot_indices[timeslot_id]
                timeslot = self.timeslots[timeslot_index]
                if timeslot_index < len(self.timeslots) - 1:
                    next_timeslot = self.timeslots[timeslot_index + 1]
                    if next_timeslot.id in times_teaching \
                            and util.contiguous(timeslot, next_timeslot):
                        next_roomslot = times_teaching[next_timeslot.id]
                        if next_roomslot.room != roomslot.room:
                            self.running_count += 1

    def process_section(self, section, roomslots):
        """Returns the number of running counts associated with this section
        assuming it is in the specified set of roomslots."""
        timeslot_pairs = []
        running_count = 0.0

        start_roomslot = roomslots[0]
        start_timeslot = start_roomslot.timeslot
        start_timeslot_idx = self.timeslot_indices[start_timeslot.id]
        if start_timeslot_idx > 0:
            prev_timeslot = self.timeslots[start_timeslot_idx - 1]
            if util.contiguous(prev_timeslot, start_timeslot):
                timeslot_pairs.append((prev_timeslot, start_timeslot))
        end_roomslot = roomslots[0]
        end_timeslot = end_roomslot.timeslot
        end_timeslot_idx = self.timeslot_indices[end_timeslot.id]
        if end_timeslot_idx < len(self.timeslots) - 1:
            next_timeslot = self.timeslots[end_timeslot_idx + 1]
            if util.contiguous(end_timeslot, next_timeslot):
                timeslot_pairs.append((end_timeslot, next_timeslot))
        for teacher in section.teachers:
            times_teaching = self.times_teacher_is_teaching[teacher.id]
            for timeslot1, timeslot2 in timeslot_pairs:
                if timeslot1.id in times_teaching \
                        and timeslot2.id in times_teaching:
                    roomslot1 = times_teaching[timeslot1.id]
                    roomslot2 = times_teaching[timeslot2.id]
                    if roomslot1.room != roomslot2.room:
                        running_count += 1
        return running_count

    @util.timed_func("TeachersWhoLikeRunningScorer")
    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        for teacher in section.teachers:
            times_teaching = self.times_teacher_is_teaching[teacher.id]
            for roomslot in roomslots:
                times_teaching[roomslot.timeslot.id] = roomslot

        self.running_count += self.process_section(section, roomslots)

    @util.timed_func("TeachersWhoLikeRunningScorer")
    def update_unschedule_section(self, section):
        """Update the internal state to reflect the unscheduling of the
        specified section."""
        roomslots = section.assigned_roomslots
        self.running_count -= self.process_section(section, roomslots)
        for teacher in section.teachers:
            times_teaching = self.times_teacher_is_teaching[teacher.id]
            for roomslot in roomslots:
                del times_teaching[roomslot.timeslot.id]
