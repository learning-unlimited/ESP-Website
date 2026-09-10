"""ILP lottery assignment. gurobipy is an optional dependency (not in core requirements.txt): the
import is guarded so its absence only makes this controller unavailable,
never breaks the rest of the app.
"""
import numpy

from esp.program.models import StudentRegistration

from .base import (
    BaseLotteryAssignmentController,
    LotteryException,
)

try:
    import gurobipy as gp
    from gurobipy import GRB
except ImportError:
    gp = None
    GRB = None


def default_empty_section_penalty_points(section_id, capacity):
    candidates = [
        (0, 1000),
        (0.3 * capacity, 100),
        (0.5 * capacity, 0),
        (capacity, 0),
    ]
    points = []
    for count, penalty in candidates:
        if points and count <= points[-1][0]:
            continue
        points.append((count, penalty))
    return points


def parse_solution_pairs(solution):
    """Parse a {varname: value} solution dict (e.g. as returned by
    RemoteSolverClient.solution()) into sparse (student_id, section_id)
    pairs -- no controller instance needed, just the
    stud_sec_assignment_{stud}_{sec} naming from _create_vars(). Used both
    by apply_remote_solution() and by the guarded-refresh capture step,
    which only needs the pairs (for LotteryRun.enrolled_pairs), not a
    full reconstructed array state."""

    prefix = "stud_sec_assignment_"
    pairs = []
    for name, value in solution.items():
        if not name.startswith(prefix) or value <= 0.5:
            continue
        stud_id_str, sec_id_str = name[len(prefix):].split("_")
        pairs.append((int(stud_id_str), int(sec_id_str)))
    return pairs


class ILPLotteryAssignmentController(BaseLotteryAssignmentController):
    """Maximizes a weighted preference objective (subject to the same hard
    constraints as the legacy algorithm -- no time conflicts, section
    capacity, lunch feasibility, one section per subject) via an integer
    program.
    """

    def __init__(self, program, **kwargs):
        if gp is None:
            raise LotteryException(
                "gurobipy is not installed; the ILP lottery algorithm is unavailable."
            )
        if kwargs.get("fill_low_priorities"):
            raise LotteryException(
                "fill_low_priorities is not yet implemented for the ILP lottery algorithm."
            )
        if kwargs.get("use_student_apps"):
            raise LotteryException(
                "use_student_apps is not supported by the ILP lottery algorithm."
            )
        if kwargs.get("max_sections"):
            raise LotteryException(
                "max_sections is not supported by the ILP lottery algorithm."
            )
        if kwargs.get("max_timeslots"):
            raise LotteryException(
                "max_timeslots is not supported by the ILP lottery algorithm."
            )

        self.rank_weights = kwargs.pop("rank_weights", None)
        self.interest_weight = kwargs.pop("interest_weight", 0.5)
        self.section_len_to_weight = kwargs.pop("section_len_to_weight", lambda length: 1)
        self.empty_student_schedule_penalties = kwargs.pop(
            "empty_student_schedule_penalties", {0: 1000, 1: 100, 2: 20}
        )
        self.empty_section_penalty_points = kwargs.pop(
            "empty_section_penalty_points", default_empty_section_penalty_points
        )
        self.deweight_by_section = kwargs.pop("deweight_by_section", False)
        self.deweight_by_timeslot = kwargs.pop("deweight_by_timeslot", True)
        self.deweight_factor = kwargs.pop("deweight_factor", None)

        super(ILPLotteryAssignmentController, self).__init__(program, **kwargs)

        # program_size_max is silently unenforced here, same as the base
        # class already does for the program_size_by_grade Tag (see
        # BaseLotteryAssignmentController.__init__) -- not a hard block, the
        # UI surfaces a persistent warning about this instead.

        has_grade_range_exception_regs = StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=self.program, relationship__name="GradeRangeException"
        ).exists()
        if self.grade_range_exceptions or has_grade_range_exception_regs:
            raise LotteryException(
                "Grade range exceptions (program.useGradeRangeExceptions() and/or "
                "GradeRangeException registrations) are not supported by the ILP lottery algorithm."
            )

        if self.rank_weights is None:
            if self.effective_priority_limit == 3:
                self.rank_weights = [5, 2, 1]
            else:
                raise LotteryException(
                    "rank_weights must be provided explicitly for a program with "
                    "%d priority levels (no default available)" % self.effective_priority_limit
                )
        if len(self.rank_weights) != self.effective_priority_limit:
            raise ValueError(
                "rank_weights (%r) must have one entry per priority level (%d)"
                % (self.rank_weights, self.effective_priority_limit)
            )
        for w in self.rank_weights:
            if w < 0:
                raise ValueError("negative weight")
        if self.interest_weight < 0:
            raise ValueError("negative weight")

        if self.deweight_by_section and self.deweight_by_timeslot:
            raise ValueError("cannot deweight by both timeslot and section")
        if self.deweight_by_section or self.deweight_by_timeslot:
            if self.deweight_factor is None:
                raise ValueError("deweight_factor is required when deweighting by timeslot or section")
            if not 0 < self.deweight_factor <= 1:
                raise ValueError("deweight_factor must be between 0 and 1")

    def initialize(self):
        """Validate + precompute the two penalty-shape params here, before
        delegating to the (much more expensive) base initialize() --
        self.num_timeslots and self.sections are already set by Base.__init__
        by the time this runs (see its call site), so a bad shape fails
        before paying for Base.initialize()'s interest/priority
        StudentRegistration extraction, not just before build_model()'s
        Gurobi work."""

        self._student_schedule_reward = self._validate_student_schedule_penalties()
        self._section_penalty_pwl = self._validate_section_penalty_points()
        super(ILPLotteryAssignmentController, self).initialize()
        # section_lengths only exists after Base.initialize() builds
        # section_schedules, so this one can't move any earlier.
        self._section_len_factor = self._validate_section_len_to_weight()

    def _validate_section_len_to_weight(self):
        section_len_factor = numpy.array(
            [self.section_len_to_weight(int(length)) for length in self.section_lengths],
            dtype=float,
        )
        if numpy.any(section_len_factor <= 0):
            raise ValueError("section_len_to_weight must return a strictly positive factor")
        return section_len_factor

    def _validate_student_schedule_penalties(self):
        T = self.num_timeslots
        for k in self.empty_student_schedule_penalties:
            if not (0 <= k <= T):
                raise ValueError(
                    "empty_student_schedule_penalties key %d is out of range -- "
                    "must be between 0 and num_timeslots (%d)" % (k, T)
                )

        reward = [0.0] * (T + 1)
        for k in range(T + 1):
            if k in self.empty_student_schedule_penalties:
                reward[k] = -self.empty_student_schedule_penalties[k]

        for k in range(1, T + 1):
            if reward[k] < reward[k - 1]:
                raise ValueError(
                    "empty_student_schedule_penalties must be monotonically non-increasing "
                    "(more filled slots should never be penalized more): penalty at %d "
                    "(%s) is less than penalty at %d (%s)" % (k - 1, -reward[k - 1], k, -reward[k])
                )
        return reward

    def _validate_section_penalty_points(self):
        pwl_by_section = {}
        for section in self.sections:
            sec_id = int(section.id)
            cap = int(section.capacity)

            points = self.empty_section_penalty_points(sec_id, cap)
            for count, penalty in points:
                if count < 0:
                    raise ValueError(
                        "empty_section_penalty_points for section %d must have non-negative "
                        "counts (got %r)" % (sec_id, count)
                    )
            if not points or points[0][0] != 0:
                raise ValueError(
                    "empty_section_penalty_points for section %d must include a point at count 0" % sec_id
                )
            if points[-1][0] != cap:
                raise ValueError(
                    "empty_section_penalty_points for section %d must include a point at "
                    "count == cap (%d)" % (sec_id, cap)
                )
            for (count_prev, penalty_prev), (count, penalty) in zip(points, points[1:]):
                if count <= count_prev:
                    raise ValueError(
                        "empty_section_penalty_points for section %d must have strictly "
                        "increasing counts: %d does not follow %d" % (sec_id, count, count_prev)
                    )
                if penalty > penalty_prev:
                    raise ValueError(
                        "empty_section_penalty_points for section %d must be monotonically "
                        "non-increasing (more enrolled should never be penalized more): penalty "
                        "at count %d (%d) exceeds penalty at count %d (%d)"
                        % (sec_id, count, penalty, count_prev, penalty_prev)
                    )

            breakpoints = [count for count, _ in points]
            reward = [-penalty for _, penalty in points]
            pwl_by_section[sec_id] = (breakpoints, reward)
        return pwl_by_section

    # ------------------------------------------------------------------
    # Model construction
    # ------------------------------------------------------------------

    def build_model(self):
        """Construct self.model (a gurobipy Model) from the frozen arrays
        initialize() already populated. Does not solve it."""

        self.model = gp.Model()
        self._setup_pref_weight()
        self._create_vars()
        self._setup_deweight_contributions()
        self._setup_constraint_no_conflicts()
        self._setup_constraint_section_capacity()
        self._setup_constraint_no_same_subject()
        self._setup_constraint_lunch()
        self.model.update()
        self._setup_objective()
        return self.model

    def _setup_pref_weight(self):
        """pref_weight[si, sj] = the best applicable weight for student si
        ranking/starring section sj, or 0 if they never did. Vectorized over
        the (num_students x num_sections) priority/interest matrices Base
        already built."""

        # Precomputed + validated in __init__ -- see _validate_section_len_to_weight().
        section_len_factor = self._section_len_factor

        grade_ok = None
        if self.options["check_grade"]:
            grade_ok = (self.student_grades[:, None] >= self.section_grade_min[None, :]) & (
                self.student_grades[:, None] <= self.section_grade_max[None, :]
            )

        weight = numpy.zeros((self.num_students, self.num_sections))
        for i in range(1, self.effective_priority_limit + 1):
            level_weight = self.priority[i] * (self.rank_weights[i - 1] * section_len_factor)[None, :]
            # The grade-range-exception priority level intentionally bypasses
            # the grade filter (mirrors LegacyLotteryAssignmentController.fill_section).
            if grade_ok is not None and not (i == self.effective_priority_limit and self.grade_range_exceptions):
                level_weight = level_weight * grade_ok
            numpy.maximum(weight, level_weight, out=weight)

        interest_contribution = self.interest * (self.interest_weight * section_len_factor)[None, :]
        if grade_ok is not None:
            interest_contribution = interest_contribution * grade_ok
        numpy.maximum(weight, interest_contribution, out=weight)

        self.pref_weight = weight
        self.pref_student_idxs, self.pref_section_idxs = numpy.nonzero(weight)

    def _create_vars(self):
        self.lp_vars = {}
        self.student_pref_sections = {si: [] for si in range(self.num_students)}
        self.section_pref_students = {sj: [] for sj in range(self.num_sections)}
        for si, sj in zip(self.pref_student_idxs.tolist(), self.pref_section_idxs.tolist()):
            self.lp_vars[(si, sj)] = self.model.addVar(
                vtype=GRB.BINARY,
                name="stud_sec_assignment_%d_%d" % (self.student_ids[si], self.section_ids[sj]),
            )
            self.student_pref_sections[si].append(sj)
            self.section_pref_students[sj].append(si)

    def _setup_deweight_contributions(self):
        """This concave-epigraph encoding is exact without PWL/indicator constraints."""

        self.deweight_terms = []
        if not (self.deweight_by_timeslot or self.deweight_by_section):
            return

        T = self.num_timeslots
        cumulative_discount = [0.0] * (T + 1)
        for k in range(1, T + 1):
            cumulative_discount[k] = cumulative_discount[k - 1] + self.deweight_factor ** (k - 1)

        for si in range(self.num_students):
            candidates = sorted(
                self.student_pref_sections[si], key=lambda sj: (-self.pref_weight[si, sj], sj)
            )
            m = len(candidates)
            if m == 0:
                continue
            weights = [self.pref_weight[si, sj] for sj in candidates]

            prefix_expr = gp.LinExpr()
            for j, sj in enumerate(candidates):
                sec_len = int(self.section_lengths[sj]) if self.deweight_by_timeslot else 1
                prefix_expr = prefix_expr + self.lp_vars[(si, sj)] * sec_len

                coeff = weights[j] if j == m - 1 else (weights[j] - weights[j + 1])
                if coeff <= 0:
                    continue  # tied with the next candidate -- contributes nothing extra

                y = self.model.addVar(
                    lb=0, ub=cumulative_discount[T], name="deweight_y_%d_%d" % (self.student_ids[si], j)
                )
                for k in range(T):
                    slope = self.deweight_factor ** k
                    self.model.addConstr(y <= cumulative_discount[k] + slope * (prefix_expr - k))
                self.deweight_terms.append(coeff * y)

    def _setup_constraint_no_conflicts(self):
        for t in range(self.num_timeslots):
            sections_at_t = set(numpy.nonzero(self.section_schedules[:, t])[0].tolist())
            if not sections_at_t:
                continue
            for si in range(self.num_students):
                relevant = [sj for sj in self.student_pref_sections[si] if sj in sections_at_t]
                # a single section can't conflict with itself, so this is only
                # a real constraint once the student prefers 2+ sections at this time
                if len(relevant) >= 2:
                    self.model.addConstr(
                        gp.quicksum(self.lp_vars[(si, sj)] for sj in relevant) <= 1,
                        "no_conflicts_%d_%d" % (self.student_ids[si], self.timeslot_ids[t]),
                    )

    def _setup_constraint_section_capacity(self):
        for sj, studs in self.section_pref_students.items():
            if not studs:
                continue
            cap = int(self.section_capacities[sj])
            self.model.addConstr(
                gp.quicksum(self.lp_vars[(si, sj)] for si in studs) <= cap,
                "capacity_%d" % self.section_ids[sj],
            )

    def _setup_constraint_no_same_subject(self):
        """A student may take at most one section of a given subject."""

        for si in range(self.num_students):
            prefs = self.student_pref_sections[si]
            if len(prefs) < 2:
                continue
            by_parent = {}
            for sj in prefs:
                by_parent.setdefault(self.parent_classes[sj], []).append(sj)
            for parent_id, secs in by_parent.items():
                if len(secs) >= 2:
                    self.model.addConstr(
                        gp.quicksum(self.lp_vars[(si, sj)] for sj in secs) <= 1,
                        "no_same_subj_%d_%d" % (self.student_ids[si], parent_id),
                    )

    def _setup_constraint_lunch(self):
        """self.lunch_timeslots is a per-day array of lunch timeslot ids.
        A day's constraint is satisfied if the student is free during at
        least one of that day's lunch timeslots."""

        if self.lunch_timeslots.size == 0:
            return

        lunch_ok_vars = {}
        for si in range(self.num_students):
            for day_idx in range(self.lunch_timeslots.shape[0]):
                day_ts_ids = self.lunch_timeslots[day_idx]
                if len(day_ts_ids) == 0:
                    continue
                day_option_vars = []
                for opt_idx in range(len(day_ts_ids)):
                    var = self.model.addVar(
                        vtype=GRB.BINARY,
                        name="lunch_ok_%d_%d_%d" % (self.student_ids[si], day_idx, opt_idx),
                    )
                    lunch_ok_vars[(si, day_idx, opt_idx)] = var
                    day_option_vars.append(var)
                self.model.addConstr(
                    gp.quicksum(day_option_vars) >= 1,
                    "lunch_%d_%d" % (self.student_ids[si], day_idx),
                )

        for day_idx in range(self.lunch_timeslots.shape[0]):
            day_ts_ids = self.lunch_timeslots[day_idx]
            for opt_idx, ts_id in enumerate(day_ts_ids):
                t = self.timeslot_indices[ts_id]
                overlapping_sections = set(numpy.nonzero(self.section_schedules[:, t])[0].tolist())
                for si in range(self.num_students):
                    relevant = [sj for sj in self.student_pref_sections[si] if sj in overlapping_sections]
                    if relevant:
                        self.model.addGenConstrIndicator(
                            lunch_ok_vars[(si, day_idx, opt_idx)],
                            True,
                            gp.quicksum(self.lp_vars[(si, sj)] for sj in relevant),
                            GRB.EQUAL,
                            0,
                            name="lunch_ok_%d_%d_%d" % (self.student_ids[si], day_idx, opt_idx),
                        )

    def _setup_objective(self):
        if self.deweight_by_timeslot or self.deweight_by_section:
            preference_term = gp.quicksum(self.deweight_terms)
        else:
            preference_term = gp.quicksum(
                var * self.pref_weight[si, sj] for (si, sj), var in self.lp_vars.items()
            )
        self.model.setObjective(preference_term, GRB.MAXIMIZE)

        # setPWLObj must be called AFTER setObjective:
        if self.empty_student_schedule_penalties:
            self._setup_empty_student_schedule_penalty_pwl()
        if self.empty_section_penalty_points:
            self._setup_empty_section_penalty_pwl()

    def _setup_empty_student_schedule_penalty_pwl(self):
        T = self.num_timeslots
        reward = self._student_schedule_reward
        breakpoints = list(range(T + 1))
        self.student_total_classes_vars = {}
        for si in range(self.num_students):
            total_classes_var = self.model.addVar(
                vtype=GRB.INTEGER, lb=0, ub=T, name="total_classes_%d" % self.student_ids[si]
            )
            total_classes_expr = gp.quicksum(
                self.lp_vars[(si, sj)] for sj in self.student_pref_sections[si]
            )
            self.model.addConstr(
                total_classes_var == total_classes_expr,
                "constr_%d_total_classes" % self.student_ids[si],
            )
            self.model.setPWLObj(total_classes_var, breakpoints, reward)
            self.student_total_classes_vars[si] = total_classes_var

    def _setup_empty_section_penalty_pwl(self):
        self.section_enrolled_vars = {}
        for sj, studs in self.section_pref_students.items():
            if not studs:
                continue
            cap = int(self.section_capacities[sj])
            sec_id = int(self.section_ids[sj])
            breakpoints, reward = self._section_penalty_pwl[sec_id]

            enrolled_var = self.model.addVar(vtype=GRB.INTEGER, lb=0, ub=cap, name="enrolled_%d" % sec_id)
            enrolled_expr = gp.quicksum(self.lp_vars[(si, sj)] for si in studs)
            self.model.addConstr(enrolled_var == enrolled_expr, "constr_%d_enrolled" % sec_id)
            self.model.setPWLObj(enrolled_var, breakpoints, reward)
            self.section_enrolled_vars[sj] = enrolled_var

    # ------------------------------------------------------------------
    # Solve (local/synchronous) and result capture
    # ------------------------------------------------------------------

    def apply_solution(self):
        """Populate the same student_sections/student_schedules/
        student_enrollments/student_utilities arrays the legacy algorithm
        produces, so compute_stats()/save_assignments()/export_assignments()
        work unmodified regardless of which algorithm ran. Reads straight off
        self.lp_vars (the in-process model just solved)."""

        solution = {var.VarName: var.X for var in self.lp_vars.values()}
        self.apply_remote_solution(solution)

    def apply_remote_solution(self, solution):
        """Same as apply_solution(), but from a {varname: value} dict (e.g.
        as returned by RemoteSolverClient.solution()) instead of a live
        gurobipy Model -- build_model() and result capture can happen in
        separate processes/requests entirely, so this only depends on the
        stud_sec_assignment_{stud}_{sec} variable naming (see
        parse_solution_pairs()), not on any object that only exists within
        the process that built and solved the model."""

        self.clear_assignments()
        for student_id, section_id in parse_solution_pairs(solution):
            si = self.student_indices[student_id]
            sj = self.section_indices[section_id]
            self.student_sections[si, sj] = True
            is_priority = any(
                self.priority[i][si, sj] for i in range(1, self.effective_priority_limit + 1)
            )
            utility_per_timeslot = 1.5 if is_priority else 1.0
            for t in numpy.nonzero(self.section_schedules[sj])[0]:
                self.student_schedules[si, t] = True
                self.student_enrollments[si, t] = self.section_ids[sj]
                self.student_utilities[si] += utility_per_timeslot

    def compute_assignments(self, check_result=True):
        """Build and solve the model in-process (synchronous). For testing only.
        For real use cases, a remote solver should be used."""

        self.build_model()
        self.model.optimize()
        self.apply_solution()

        if check_result:
            self.check_assignments()
