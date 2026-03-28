__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2025 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from esp.program.class_status import ClassStatus
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator
from esp.program.models import (
    BooleanExpression, ClassCategories, ScheduleConstraint,
    ScheduleTestCategory,
)
from esp.program.models.class_ import ClassSection, ClassSubject
from esp.program.tests import ProgramFrameworkTest


class LunchConstraintGeneratorInitTest(ProgramFrameworkTest):
    """Tests for initialisation and timeslot classification."""

    def setUp(self):
        super().setUp(num_timeslots=6, timeslot_length=50, timeslot_gap=10)
        self.all_ts = list(self.program.getTimeSlots().order_by('start'))

    # ── __init__ ──────────────────────────────────────────────────────

    def test_init_classifies_timeslots_with_lunch_in_middle(self):
        """With lunch in the middle, timeslots should split into before/lunch/after."""
        lunch_ts = [self.all_ts[2], self.all_ts[3]]
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=lunch_ts, generate_constraints=False
        )
        for day, buckets in gen.days.items():
            self.assertTrue(len(buckets['before']) > 0,
                            "Expected timeslots before lunch")
            self.assertEqual(len(buckets['lunch']), 2,
                             "Expected exactly 2 lunch timeslots")
            self.assertTrue(len(buckets['after']) > 0,
                            "Expected timeslots after lunch")

    def test_init_handles_empty_lunch_timeslots(self):
        """Passing no lunch timeslots should still create day buckets."""
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=[], generate_constraints=False
        )
        for day, buckets in gen.days.items():
            self.assertEqual(len(buckets['lunch']), 0)


class LunchCategoryAndSubjectTest(ProgramFrameworkTest):
    """Tests for get_lunch_category, get_lunch_subject, get_lunch_sections."""

    def setUp(self):
        super().setUp(num_timeslots=4, timeslot_length=50, timeslot_gap=10)
        self.all_ts = list(self.program.getTimeSlots().order_by('start'))
        self.lunch_ts = [self.all_ts[1], self.all_ts[2]]
        self.gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=False
        )

    # ── get_lunch_category ────────────────────────────────────────────

    def test_get_lunch_category_creates_if_missing(self):
        """Should create a Lunch/L category when none exists."""
        ClassCategories.objects.filter(category='Lunch', symbol='L').delete()
        cat = self.gen.get_lunch_category()
        self.assertEqual(cat.category, 'Lunch')
        self.assertEqual(cat.symbol, 'L')
        self.assertIn(cat, self.program.class_categories.all())

    def test_get_lunch_category_returns_existing(self):
        """Should return the existing Lunch/L category."""
        existing, _ = ClassCategories.objects.get_or_create(
            category='Lunch', symbol='L')
        cat = self.gen.get_lunch_category()
        self.assertEqual(cat.id, existing.id)

    # ── get_lunch_subject ─────────────────────────────────────────────

    def test_get_lunch_subject_creates_new(self):
        """Creates a ClassSubject for lunch on a given day."""
        day = list(self.gen.days.keys())[0]
        subj = self.gen.get_lunch_subject(day)
        self.assertEqual(subj.title, 'Lunch Period')
        self.assertEqual(subj.parent_program, self.program)
        self.assertEqual(subj.category.category, 'Lunch')
        self.assertEqual(subj.status, ClassStatus.ACCEPTED)
        self.assertEqual(subj.message_for_directors, day.isoformat())
        self.assertEqual(subj.grade_min, 7)
        self.assertEqual(subj.grade_max, 12)

    def test_get_lunch_subject_returns_existing(self):
        """Returns the same subject on repeated calls for the same day."""
        day = list(self.gen.days.keys())[0]
        subj1 = self.gen.get_lunch_subject(day)
        subj2 = self.gen.get_lunch_subject(day)
        self.assertEqual(subj1.id, subj2.id)

    # ── get_lunch_sections ────────────────────────────────────────────

    def test_get_lunch_sections_creates_sections_for_each_timeslot(self):
        """Creates one ClassSection per lunch timeslot on the given day."""
        day = list(self.gen.days.keys())[0]
        # First call creates the subject with duration stored as string.
        # After save(), Django's DecimalField converts it to Decimal.
        # Refetch from DB so add_section sees a Decimal, not a string.
        subj = self.gen.get_lunch_subject(day)
        subj.refresh_from_db()
        sections = self.gen.get_lunch_sections(day)
        lunch_count = len(self.gen.days[day]['lunch'])
        self.assertEqual(sections.count(), lunch_count,
                         "Should have one section per lunch timeslot")
        for sec in sections:
            self.assertEqual(sec.status, ClassStatus.ACCEPTED)

    def test_get_lunch_sections_reuses_existing_sections(self):
        """Existing lunch sections should be reused and reset to accepted."""
        day = list(self.gen.days.keys())[0]
        self.gen.get_lunch_subject(day).refresh_from_db()
        sections = list(self.gen.get_lunch_sections(day))
        sections[0].status = 0
        sections[0].save()

        refreshed_sections = list(self.gen.get_lunch_sections(day))

        self.assertEqual(len(refreshed_sections), len(self.gen.days[day]['lunch']))
        self.assertTrue(all(sec.status == ClassStatus.ACCEPTED for sec in refreshed_sections))


class ApplyBinaryOpTest(ProgramFrameworkTest):
    """Tests for the boolean expression tree builder."""

    def setUp(self):
        super().setUp(num_timeslots=4, timeslot_length=50, timeslot_gap=10)
        self.gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=[], generate_constraints=False
        )

    def _make_expression(self):
        exp = BooleanExpression()
        exp.label = 'test expression'
        exp.save()
        return exp

    def test_apply_binary_op_empty_list(self):
        """Empty list of tokens should not add anything to the expression."""
        exp = self._make_expression()
        initial_count = exp.booleantoken_set.count()
        self.gen.apply_binary_op_to_list(exp, 'OR', '0', [])
        self.assertEqual(exp.booleantoken_set.count(), initial_count)

    def test_apply_binary_op_single_token(self):
        """Single token list should produce: token, identity, operator."""
        exp = self._make_expression()
        # We can use a ScheduleTestCategory as a real token
        ts = list(self.program.getTimeSlots().order_by('start'))
        cat, _ = ClassCategories.objects.get_or_create(category='Lunch', symbol='L')
        real_token = ScheduleTestCategory()
        real_token.timeblock_id = ts[0].id
        real_token.exp_id = exp.id
        real_token.category = cat
        self.gen.apply_binary_op_to_list(exp, 'OR', '0', [real_token])
        # Should have 3 tokens: the real token, '0' identity, and 'OR' operator
        self.assertEqual(exp.booleantoken_set.count(), 3)

    def test_apply_binary_op_two_tokens(self):
        """Two-token list should produce: token, token, operator (3 total)."""
        exp = self._make_expression()
        ts = list(self.program.getTimeSlots().order_by('start'))
        cat, _ = ClassCategories.objects.get_or_create(category='Lunch', symbol='L')
        tokens = []
        for t in ts[:2]:
            tok = ScheduleTestCategory()
            tok.timeblock_id = t.id
            tok.exp_id = exp.id
            tok.category = cat
            tokens.append(tok)
        self.gen.apply_binary_op_to_list(exp, 'OR', '0', tokens)
        self.assertEqual(exp.booleantoken_set.count(), 3)

    def test_apply_binary_op_many_tokens_recurses(self):
        """Four tokens should recurse into two halves and add a final operator."""
        exp = self._make_expression()
        ts = list(self.program.getTimeSlots().order_by('start'))
        cat, _ = ClassCategories.objects.get_or_create(category='Lunch', symbol='L')
        tokens = []
        for t in ts:
            tok = ScheduleTestCategory()
            tok.timeblock_id = t.id
            tok.exp_id = exp.id
            tok.category = cat
            tokens.append(tok)
        self.gen.apply_binary_op_to_list(exp, 'OR', '0', tokens)
        self.assertEqual(exp.booleantoken_set.count(), 7)


class ClearExistingConstraintsTest(ProgramFrameworkTest):
    """Tests for constraint cleanup."""

    def setUp(self):
        super().setUp(num_timeslots=4, timeslot_length=50, timeslot_gap=10)
        self.all_ts = list(self.program.getTimeSlots().order_by('start'))
        self.lunch_ts = [self.all_ts[1], self.all_ts[2]]
        self.gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=True, autocorrect=False
        )

    def test_clear_existing_constraints_removes_schedule_constraints(self):
        """Generating then clearing should leave no ScheduleConstraints."""
        # Generate constraints first
        self.gen.generate_all_constraints()
        self.assertTrue(
            ScheduleConstraint.objects.filter(program=self.program).exists(),
            "Constraints should exist after generation"
        )
        # Now clear
        self.gen.clear_existing_constraints()
        self.assertFalse(
            ScheduleConstraint.objects.filter(program=self.program).exists(),
            "Constraints should be gone after clearing"
        )

    def test_clear_existing_constraints_removes_stale_lunch_sections_and_subjects(self):
        """Lunch sections outside configured lunch slots and empty subjects should be deleted."""
        day = list(self.gen.days.keys())[0]
        lunch_subject = self.gen.get_lunch_subject(day)
        lunch_subject.refresh_from_db()
        stale_section = lunch_subject.add_section(status=ClassStatus.ACCEPTED)
        stale_section.meeting_times.add(self.all_ts[0])

        orphan_subject = ClassSubject.objects.create(
            parent_program=self.program,
            category=self.gen.get_lunch_category(),
            title='Unused Lunch',
            class_size_max=10,
            grade_min=7,
            grade_max=12,
            status=ClassStatus.ACCEPTED,
            message_for_directors=day.isoformat(),
        )

        self.gen.clear_existing_constraints()

        self.assertFalse(
            ClassSection.objects.filter(id=stale_section.id).exists(),
            "Stale lunch sections outside configured lunch slots should be deleted",
        )
        self.assertFalse(
            ClassSubject.objects.filter(id=orphan_subject.id).exists(),
            "Empty lunch subjects should be deleted",
        )


class GenerateConstraintTest(ProgramFrameworkTest):
    """Integration tests for end-to-end constraint generation."""

    def setUp(self):
        super().setUp(num_timeslots=4, timeslot_length=50, timeslot_gap=10)
        self.all_ts = list(self.program.getTimeSlots().order_by('start'))
        self.lunch_ts = [self.all_ts[1], self.all_ts[2]]

    def test_generate_constraint_creates_db_objects(self):
        """generate_constraint should create ScheduleConstraint + BooleanExpressions."""
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=False, autocorrect=False
        )
        day = list(gen.days.keys())[0]
        subj = gen.get_lunch_subject(day)
        subj.refresh_from_db()
        gen.get_lunch_sections(day)
        gen.generate_constraint(day)

        constraints = ScheduleConstraint.objects.filter(program=self.program)
        self.assertEqual(constraints.count(), 1)
        constraint = constraints[0]
        self.assertIsNotNone(constraint.condition)
        self.assertIsNotNone(constraint.requirement)

    def test_generate_constraint_with_conditions_adds_and_operator(self):
        """When conditions are enabled, the check expression should combine halves with AND."""
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=False, include_conditions=True,
            autocorrect=False
        )
        day = list(gen.days.keys())[0]
        subj = gen.get_lunch_subject(day)
        subj.refresh_from_db()
        gen.get_lunch_sections(day)
        gen.generate_constraint(day)

        constraint = ScheduleConstraint.objects.filter(program=self.program).first()
        tokens = list(constraint.condition.booleantoken_set.values_list('text', flat=True))
        self.assertIn('AND', tokens)

    def test_get_failure_function_lists_lunch_timeslot_ids(self):
        """Failure-function code should embed the configured lunch timeslot ids."""
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=True, autocorrect=True
        )
        day = list(gen.days.keys())[0]
        failure_code = gen.get_failure_function(day)

        for timeslot in self.lunch_ts:
            self.assertIn(str(timeslot.id), failure_code)
        self.assertIn('lunch_choices', failure_code)

    def test_generate_all_constraints_creates_per_day(self):
        """generate_all_constraints creates constraints for each day with lunch."""
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=True, autocorrect=False
        )
        gen.generate_all_constraints()

        num_days_with_lunch = sum(
            1 for d in gen.days if gen.days[d]['lunch']
        )
        constraints = ScheduleConstraint.objects.filter(program=self.program)
        self.assertEqual(constraints.count(), num_days_with_lunch)

    def test_generate_all_constraints_skips_days_without_lunch(self):
        """Days that have no lunch timeslots should not produce constraints."""
        # Use only timeslots from a secondary day (which won't have lunch)
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=[],
            generate_constraints=True, autocorrect=False
        )
        gen.generate_all_constraints()
        self.assertEqual(
            ScheduleConstraint.objects.filter(program=self.program).count(), 0,
            "No constraints should be generated when there are no lunch timeslots"
        )

    def test_generate_all_constraints_without_generation_still_creates_sections(self):
        """Lunch sections should still be created when constraints are disabled."""
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=False, autocorrect=False
        )
        gen.generate_all_constraints()

        self.assertEqual(
            ScheduleConstraint.objects.filter(program=self.program).count(), 0,
            "No constraints should be generated when generation is disabled",
        )
        day = list(gen.days.keys())[0]
        self.assertEqual(
            gen.get_lunch_sections(day).count(),
            len(gen.days[day]['lunch']),
            "Lunch sections should still be created for each lunch timeslot",
        )

    def test_generate_constraint_with_autocorrect(self):
        """When autocorrect=True, constraint.on_failure should contain code."""
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=True, autocorrect=True
        )
        gen.generate_all_constraints()

        constraint = ScheduleConstraint.objects.filter(
            program=self.program
        ).first()
        self.assertIn('lunch_choices', constraint.on_failure,
                       "on_failure code should reference lunch_choices")

    def test_generate_constraint_without_conditions(self):
        """When include_conditions=False, check expression should have '1' token."""
        gen = LunchConstraintGenerator(
            self.program, lunch_timeslots=self.lunch_ts,
            generate_constraints=True, include_conditions=False,
            autocorrect=False
        )
        gen.generate_all_constraints()

        constraint = ScheduleConstraint.objects.filter(
            program=self.program
        ).first()
        # The condition expression should contain a '1' (always-true) token
        tokens = list(constraint.condition.booleantoken_set.values_list(
            'text', flat=True
        ))
        self.assertIn('1', tokens,
                       "Condition should have '1' token when conditions disabled")
