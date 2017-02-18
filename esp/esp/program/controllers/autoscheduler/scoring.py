"""A Scorer can score a schedule, or (for performance reasons) predict the
change in score a particular schedule hypothetical schedule manipulation would
cause. Since some of these scorers are fairly global, e.g. depend on a
distribution, scorers are allowed to maintain an internal state; so a scorer
can initialize (or re-initialize) to a schedule, score the schedule it is
currently set to, predict a score for a hypothetical change (without changing
its state), or perform a change (i.e. updating its state).

A Scorer is expected to return a score in the range [0, 1], where 1 is good and
0 is bad.
"""
import esp.program.controllers.autoscheduler.util as util
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
        self.update_unschedule_section(section)
        self.update_schedule_section(section, start_roomslot)

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        raise NotImplementedError

    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        self.update_move_section(section1, section2.assigned_roomslots[0])
        self.update_move_section(section2, section1.assigned_roomslots[0])

    # I've commented out all the predictive scorers because they aren't
    # strictly necessary; unlike constraints, which need to prune illegal
    # operations, you can always just make the operation, score it, and then
    # undo it. It's a little slower but if implemented correctly shouldn't be
    # much slower.
    # def score_schedule_section(self, section, start_roomslot):
    #     """Returns a score in the range [0, 1] if the schedule currently
    #     reflected in internal state schedules the specified section starting
    #     at the specified roomslot."""
    #     raise NotImplementedError

    # def score_move_section(self, section, start_roomslot):
    #     """Returns a score in the range [0, 1] if the schedule currently
    #     reflected in internal state moves the specified already-scheduled
    #     section to start at the specified roomslot."""
    #     raise NotImplementedError

    # def score_unschedule_section(self, section):
    #     """Returns a score in the range [0, 1] if the schedule currently
    #     reflected in internal state unschedules the specified section."""
    #     raise NotImplementedError

    # def score_swap_sections(self, section1, section2):
    #     """Returns a score in the range [0, 1] if the schedule currently
    #     reflected in internal state swaps the two specified already-scheduled
    #     sections."""
    #     raise NotImplementedError


class CompositeScorer(BaseScorer):
    """A scorer which checks all the scorers you actually want, and weights them
    according to pre-specified weights."""
    def __init__(self, scorer_names_and_weights, schedule):
        """Takes in a list of pairs of scorer names (as strings) and weights (as
        floats), and loads them, initializing them to the specified schedule.
        All weights should be positive."""
        self.scorers_and_weights = []
        if len(scorer_names_and_weights) == 0:
            # If we didn't receive any names and weights, we are a trivial
            # scorer. Set total weight to 1 to avoid division by 0.
            self.total_weight = 1.0
        else:
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
        current state. This should be implemented efficiently so it can be
        called frequently."""
        total_score = 0.0
        for scorer, weight in self.scorers_and_weights:
            total_score += scorer.score_schedule() * weight
        return total_score / self.total_weight

    # See note in BaseScorer about these being commented out.
    #
    # def score_schedule_section(self, section, start_roomslot):
    #     """Returns a score in the range [0, 1] if the schedule currently
    #     reflected in internal state schedules the specified section starting
    #     at the specified roomslot."""
    #     total_score = 0.0
    #     for scorer, weight in self.scorers_and_weights:
    #         total_score += \
    #             scorer.score_schedule_section(
    #                 section, start_roomslot) * weight
    #     return total_score / self.total_weight

    # def score_move_section(self, section, start_roomslot):
    #     """Returns a score in the range [0, 1] if the schedule currently
    #     reflected in internal state moves the specified already-scheduled
    #     section to start at the specified roomslot."""
    #     total_score = 0.0
    #     for scorer, weight in self.scorers_and_weights:
    #         total_score += \
    #             scorer.score_move_section(section, start_roomslot) * weight
    #     return total_score / self.total_weight

    # def score_unschedule_section(self, section):
    #     """Returns a score in the range [0, 1] if the schedule currently
    #     reflected in internal state unschedules the specified section."""
    #     total_score = 0.0
    #     for scorer, weight in self.scorers_and_weights:
    #         total_score += \
    #             scorer.score_unschedule_section(section) * weight
    #     return total_score / self.total_weight

    # def score_swap_sections(self, section1, section2):
    #     """Returns a score in the range [0, 1] if the schedule currently
    #     reflected in internal state swaps the two specified already-scheduled
    #     sections."""
    #     total_score = 0.0
    #     for scorer, weight in self.scorers_and_weights:
    #         total_score += \
    #             scorer.score_swap_sections(section1, section2) * weight
    #     return total_score / self.total_weight

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
            if t.day == prev_timeslot.day:
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

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        for teacher in section.teachers:
            if teacher.is_admin:
                for roomslot in roomslots:
                    self.admins_per_timeslot[roomslot.timeslot.id] += 1

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        for teacher in section.teachers:
            if teacher.is_admin:
                for roomslot in section.assigned_roomslots:
                    self.admins_per_timeslot[roomslot.timeslot.id] -= 1


class CategoryBalanceScorer(BaseScorer):
    """Each category should have its student-capacity spread out evenly over
    the timeblocks in each day."""

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
                fractional_capacity = \
                    capacity * timeslot.duration / student_class_hours
                if fractional_capacity > leeway:
                    total_penalty += capacity / student_class_hours - leeway
        return 1 - (total_penalty / len(self.student_class_hours_by_category))

    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
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

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        roomslots = start_roomslot.room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        for roomslot in roomslots:
            actual_capacity = min(section.capacity, roomslot.room.capacity)
            self.capacity_per_timeslot_by_category[section.category][
                roomslot.timeslot.id] += actual_capacity

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        for roomslot in section.assigned_roomslots:
            actual_capacity = min(section.capacity, roomslot.room.capacity)
            self.capacity_per_timeslot_by_category[section.category][
                roomslot.timeslot.id] -= actual_capacity


class LunchStudentClassHoursScorer(BaseScorer):
    """Preferentially schedule student-class-hours during non-lunch blocks,
    assuming (some fraction of) students are required to have lunch during
    those times so there will be less demand."""

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # We return simply the fraction of all possible student-class-hours
        # which are scheduled during non-lunch timeslots. Note that this is an
        # underestimate because the denominator accounts for time between
        # timeslots in multi-hour classes, and the numerator does not.
        return self.non_lunch_student_class_hours / \
            self.total_student_class_hours

    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        self.lunch_timeslots = set()
        for timeslots in schedule.lunch_timeslots.itervalues():
            self.lunch_timeslots.update([t.id for t in timeslots])
        self.total_student_class_hours = float(sum(
            [sec.capacity * sec.duration for sec in
             schedule.class_sections.iteritems()]))
        self.non_lunch_student_class_hours = 0.0
        for section in schedule.class_sections.itervalues():
            for roomslot in section.assigned_roomslots:
                actual_capacity = min(section.capacity, roomslot.room.capacity)
                if roomslot.timeslot.id not in self.lunch_timeslots:
                    self.non_lunch_student_class_hours += \
                        actual_capacity * roomslot.timeslot.duration

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

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        for roomslot in section.assigned_roomslots:
            actual_capacity = min(section.capacity, roomslot.room.capacity)
            if roomslot.timeslot.id not in self.lunch_timeslots:
                self.non_lunch_student_class_hours -= \
                    actual_capacity * roomslot.timeslot.duration


class HungryTeacherScorer(BaseScorer):
    """Avoid teachers having to teach during both blocks of lunch."""

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the total fraction of non-hungry teachers.
        return 1 - len(self.hungry_teachers) / self.total_teachers

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

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
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
            if all([timeslots_teaching[t] for t in timeslots]):
                self.hungry_teachers.add(teacher_id)
                return
        if teacher_id in self.hungry_teachers:
            self.hungry_teachers.remove(teacher_id)


class NumSectionsScorer(BaseScorer):
    """Schedule as many sections as possible."""

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the fraction of sections which are scheduled.
        return self.scheduled_sections / self.total_sections

    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        self.total_sections = float(len(schedule.class_sections))
        self.scheduled_sections = sum(
            [s.is_scheduled() for s in schedule.class_sections.itervalues()])

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        self.scheduled_sections += 1

    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        pass

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        assert self.scheduled_sections > 0
        self.scheduled_sections -= 1

    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        pass


class NumSubjectsScorer(BaseScorer):
    """Schedule as many unique classes (i.e. subjects) as possible."""

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the fraction of subjects which are scheduled.
        return self.scheduled_subjects / self.total_subjects

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

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        self.num_scheduled_sections_by_subject[section.parent_class] += 1
        if self.num_scheduled_sections_by_subject[section.parent_class] == 1:
            self.scheduled_sections += 1

    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        pass

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        assert self.num_scheduled_sections_by_subject[section.parent_class] > 0
        self.num_scheduled_sections_by_subject[section.parent_class] -= 1
        if self.num_scheduled_sections_by_subject[section.parent_class] == 0:
            self.scheduled_sections -= 1

    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        pass


class NumTeachersScorer(BaseScorer):
    """Schedule as many distinct teachers' classes as possible."""

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return the fraction of teachers which have scheduled classes.
        return self.scheduled_teachers / self.total_teachers

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

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        for t in section.teachers:
            self.num_scheduled_sections_by_teacher[t.id] += 1
            if self.num_scheduled_sections_by_teacher[t.id] == 1:
                self.scheduled_teachers += 1

    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        pass

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        for t in section.teachers:
            assert self.num_scheduled_sections_by_teacher[t.id] > 0
            self.num_scheduled_sections_by_teacher[t.id] -= 1
            if self.num_scheduled_sections_by_teacher[t.id] == 0:
                self.scheduled_teachers -= 1

    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
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

    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        # Return simply the fraction of all sections which are nonfollowed.
        return self.nonfollowed_sections / self.num_sections

    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        self.num_sections = float(len(schedule.class_sections))
        # A count of the number of sections which don't immediately have a
        # following section.
        self.nonfollowed_sections = 0.0
        for section in schedule.class_sections.itervalues():
            if section.is_scheduled():
                last_roomslot = section.assigned_roomslots[-1]
                next_roomslot = last_roomslot.next()
                if next_roomslot is None \
                        or next_roomslot.assigned_section is None \
                        or not util.contiguous(
                            last_roomslot.timeslot, next_roomslot.timeslot):
                    self.nonfollowed_sections += 1

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        room = start_roomslot.room
        roomslots = room.get_roomslots_by_duration(
            start_roomslot, section.duration)
        nonfollowed_sections_delta = 1
        start_idx = start_roomslot.index()
        if start_idx > 0:
            prev_roomslot = room.availability[start_idx - 1]
            if prev_roomslot.assigned_section is not None \
                    and util.contiguous(
                        prev_roomslot.timeslot, start_roomslot.timeslot):
                nonfollowed_sections_delta -= 1
        last_roomslot = roomslots[-1]
        next_roomslot = last_roomslot.next()
        if next_roomslot is not None \
                and next_roomslot.assigned_section is not None \
                and util.contiguous(
                    last_roomslot.timeslot, next_roomslot.timeslot):
            nonfollowed_sections_delta -= 1
        self.nonfollowed_sections += nonfollowed_sections_delta

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        roomslots = section.assigned_roomslots
        start_roomslot = roomslots[0]
        room = start_roomslot.room
        nonfollowed_sections_delta = -1
        start_idx = start_roomslot.index()
        if start_idx > 0:
            prev_roomslot = room.availability[start_idx - 1]
            if prev_roomslot.assigned_section is not None \
                    and util.contiguous(
                        prev_roomslot.timeslot, start_roomslot.timeslot):
                nonfollowed_sections_delta += 1
        last_roomslot = roomslots[-1]
        next_roomslot = last_roomslot.next()
        if next_roomslot is not None \
                and next_roomslot.assigned_section is not None \
                and util.contiguous(
                    last_roomslot.timeslot, next_roomslot.timeslot):
            nonfollowed_sections_delta += 1
        self.nonfollowed_sections += nonfollowed_sections_delta


class RoomSizeMismatchScorer(BaseScorer):
    """Match room sizes to classes as much as possible."""
    # Make sure this doesn't get really sad trying to schedule a 200-capacity
    # class in 26-100, or a 600-capacity class in 1-190
    def score_schedule(self):
        """Returns a score in the range [0, 1] for the schedule reflected in its
        current state."""
        raise NotImplementedError

    def update_schedule(self, schedule):
        """Overwrite internal state to reflect the given schedule."""
        # To deal with huge rooms and classes, if any class is larger than the
        # largest room, we consider its capacity to just match that of the
        # largest room, and vice versa.
        self.max_class_size = max(
            [s.capacity for s in schedule.class_sections.itervalues()])
        self.max_room_size = max(
            [c.capacity for c in schedule.classrooms.itervalues()])
        pass  # TODO

    def update_schedule_section(self, section, start_roomslot):
        """Update the internal state to reflect the scheduling of the specified
        section to start at the specified roomslot."""
        raise NotImplementedError

    def update_move_section(self, section, start_roomslot):
        """Update the internal state to reflect the moving of the specified
        already-scheduled section to start at the specified roomslot."""
        self.update_unschedule_section(section)
        self.update_schedule_section(section, start_roomslot)

    def update_unschedule_section(self, section):
        """Update the internal state to reflect the uncsheduling of the
        specified section."""
        raise NotImplementedError

    def update_swap_sections(self, section1, section2):
        """Update the internal state to reflect the swapping of the two
        specified sections."""
        self.update_move_section(section1, section2.assigned_roomslots[0])
        self.update_move_section(section2, section1.assigned_roomslots[0])


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
