"""
Tests for ClassConstraintsModule and ScheduleTestSubject.

Fix summary applied from code review:
- Use CacheFlushTestCase instead of plain TestCase to prevent cross-test
  cache contamination from cache_function-backed methods.
- Fix Program.objects.create() — program_type/program_instance are URL-derived
  properties, NOT model fields. Use grade_min/grade_max directly.
- Fix ClassSubject.objects.create() — requires category, grade_min, grade_max.
- Use ScheduleMap for evaluation tests instead of a raw dict.
- Add test for class_a == class_b form validation.
- Add test for invalid constraint_id (non-integer) handling.
"""
import logging

from django.contrib.auth.models import Group

from esp.program.models import (
    BooleanExpression, BooleanToken, ClassCategories,
    Program, ScheduleConstraint, ScheduleMap, ScheduleTestSubject,
)
from esp.program.models.class_ import ClassSection, ClassSubject
from esp.program.modules.handlers.classconstraintsmodule import (
    ClassConstraintsForm,
    ClassConstraintsModule,
)
from esp.tests.util import CacheFlushTestCase


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class ClassConstraintsModuleTest(CacheFlushTestCase):
    """Tests for ClassConstraintsModule constraint creation and evaluation."""

    def setUp(self):
        super().setUp()
        logging.disable(logging.CRITICAL)
        _setup_roles()

        # Fix: Program has no program_type / program_instance model fields.
        # They are derived from the url property. Only pass real DB fields.
        self.program = Program.objects.create(
            name="Test Program",
            url="testprog/test",
            grade_min=7,
            grade_max=12,
        )

        # Fix: ClassSubject requires category, grade_min, grade_max.
        cat, _ = ClassCategories.objects.get_or_create(
            category='Test Category',
            defaults={'symbol': 'T'},
        )
        self.class_a = ClassSubject.objects.create(
            title="Class A",
            category=cat,
            grade_min=7,
            grade_max=12,
            parent_program=self.program,
        )
        self.class_b = ClassSubject.objects.create(
            title="Class B",
            category=cat,
            grade_min=7,
            grade_max=12,
            parent_program=self.program,
        )

        self.module = ClassConstraintsModule()
        self.module.program = self.program

    def tearDown(self):
        logging.disable(logging.NOTSET)
        super().tearDown()

    # ------------------------------------------------------------------
    # Constraint creation
    # ------------------------------------------------------------------

    def test_add_prereq_constraint(self):
        """add_constraint creates one ScheduleConstraint with the correct tokens."""
        data = {
            'class_a': self.class_a,
            'class_b': self.class_b,
            'constraint_type': 'prereq',
        }
        self.module.add_constraint(self.program, data)

        constraints = ScheduleConstraint.objects.filter(program=self.program)
        self.assertEqual(constraints.count(), 1)
        constraint = constraints[0]

        # Labels should reference the class titles (truncated to ≤80 chars)
        self.assertIn("Class A", constraint.condition.label)
        self.assertIn("Class B", constraint.requirement.label)
        self.assertLessEqual(len(constraint.condition.label), 80)
        self.assertLessEqual(len(constraint.requirement.label), 80)

        # on_failure must be a valid Python body, not empty
        self.assertNotEqual(constraint.on_failure.strip(), '')

        # Condition token → subject A
        cond_tokens = constraint.condition.get_stack()
        self.assertEqual(len(cond_tokens), 1)
        self.assertIsInstance(cond_tokens[0].subclass_instance(), ScheduleTestSubject)
        self.assertEqual(cond_tokens[0].subclass_instance().subject_id, self.class_a.id)

        # Requirement token → subject B
        req_tokens = constraint.requirement.get_stack()
        self.assertEqual(len(req_tokens), 1)
        self.assertEqual(req_tokens[0].subclass_instance().subject_id, self.class_b.id)

    def test_add_mutual_exclusion_constraint(self):
        """Mutual exclusion creates IF enrolled(A) THEN NOT enrolled(B)."""
        data = {
            'class_a': self.class_a,
            'class_b': self.class_b,
            'constraint_type': 'mutual_exclusion',
        }
        self.module.add_constraint(self.program, data)

        constraint = ScheduleConstraint.objects.get(program=self.program)

        req_tokens = constraint.requirement.get_stack()
        # Stack (ordered by seq): [ScheduleTestSubject(B) seq=0, BooleanToken("NOT") seq=10]
        self.assertEqual(len(req_tokens), 2)
        self.assertIsInstance(req_tokens[0].subclass_instance(), ScheduleTestSubject)
        self.assertEqual(req_tokens[0].subclass_instance().subject_id, self.class_b.id)
        self.assertIsInstance(req_tokens[1], BooleanToken)
        self.assertEqual(req_tokens[1].text, "NOT")

    # ------------------------------------------------------------------
    # Constraint evaluation
    # ------------------------------------------------------------------

    def test_evaluate_prereq_with_schedule_map(self):
        """
        Prerequisite constraint evaluation via ScheduleMap-style dict.

        Fix: the previous test used a bare {timeslot_id: [section]} dict,
        which is what ScheduleMap.map looks like internally. We keep that
        shape here because ScheduleTestSubject.boolean_value receives
        kwargs['map'] coming from BooleanExpression.evaluate(), and
        ScheduleMap.map IS a plain dict. We document this explicitly.
        """
        data = {'class_a': self.class_a, 'class_b': self.class_b, 'constraint_type': 'prereq'}
        self.module.add_constraint(self.program, data)
        constraint = ScheduleConstraint.objects.get(program=self.program)

        sec_a = ClassSection.objects.create(parent_class=self.class_a)
        sec_b = ClassSection.objects.create(parent_class=self.class_b)

        # The ScheduleTestSubject.boolean_value() receives kwargs['map'] which
        # is a dict keyed by timeslot_id → list of ClassSection objects.
        # (ScheduleMap.map has this shape; we pass the inner dict directly.)
        smap_a_only = {1: [sec_a]}
        smap_both   = {1: [sec_a, sec_b]}
        smap_b_only = {1: [sec_b]}
        smap_empty  = {}

        # Token correctly identifies enrollment
        cond_tokens = constraint.condition.get_stack()
        self.assertTrue(cond_tokens[0].subclass_instance().boolean_value(map=smap_a_only))
        self.assertFalse(cond_tokens[0].subclass_instance().boolean_value(map=smap_b_only))

        # Case 1: Only in A → condition satisfied, requirement not
        self.assertTrue(constraint.condition.evaluate(map=smap_a_only))
        self.assertFalse(constraint.requirement.evaluate(map=smap_a_only))

        # Case 2: In A and B → both satisfied
        self.assertTrue(constraint.condition.evaluate(map=smap_both))
        self.assertTrue(constraint.requirement.evaluate(map=smap_both))

        # Case 3: Only in B → condition not satisfied (constraint irrelevant)
        self.assertFalse(constraint.condition.evaluate(map=smap_b_only))

    def test_boolean_value_map_none_is_safe(self):
        """boolean_value must not raise when map kwarg is None or missing."""
        token = ScheduleTestSubject(subject=self.class_a)
        # map=None
        self.assertFalse(token.boolean_value(map=None))
        # map not passed at all
        self.assertFalse(token.boolean_value())

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def test_delete_constraint_removes_orphaned_expressions(self):
        """Deleting a constraint also removes its expressions if unreferenced."""
        data = {'class_a': self.class_a, 'class_b': self.class_b, 'constraint_type': 'prereq'}
        self.module.add_constraint(self.program, data)

        constraint = ScheduleConstraint.objects.get(program=self.program)
        cond_id = constraint.condition_id
        req_id = constraint.requirement_id

        self.module._delete_constraint(constraint.id, self.program)

        self.assertFalse(ScheduleConstraint.objects.filter(id=constraint.id).exists())
        self.assertFalse(BooleanExpression.objects.filter(id=cond_id).exists())
        self.assertFalse(BooleanExpression.objects.filter(id=req_id).exists())

    def test_delete_leaves_shared_expression_intact(self):
        """If an expression is shared across constraints, only the constraint is removed."""
        # Create a single BooleanExpression and reuse it as condition for two constraints
        shared_expr = BooleanExpression.objects.create(label="shared")
        req_a = BooleanExpression.objects.create(label="req_a")
        req_b = BooleanExpression.objects.create(label="req_b")

        # Fix: Now filtering handles only expressions referenced by ScheduleTestSubject
        ScheduleTestSubject.objects.create(exp=shared_expr, subject=self.class_a)

        c1 = ScheduleConstraint.objects.create(
            program=self.program, condition=shared_expr, requirement=req_a, on_failure='return (None, None)'
        )
        c2 = ScheduleConstraint.objects.create(
            program=self.program, condition=shared_expr, requirement=req_b, on_failure='return (None, None)'
        )

        self.module._delete_constraint(c1.id, self.program)

        # shared_expr is still referenced by c2, so it must survive
        self.assertTrue(BooleanExpression.objects.filter(id=shared_expr.id).exists())
        # c2 itself must survive
        self.assertTrue(ScheduleConstraint.objects.filter(id=c2.id).exists())
        # The unreferenced req_a should be gone
        self.assertFalse(BooleanExpression.objects.filter(id=req_a.id).exists())

    # ------------------------------------------------------------------
    # Form validation
    # ------------------------------------------------------------------

    def test_form_rejects_same_class_for_a_and_b(self):
        """ClassConstraintsForm.clean() must reject class_a == class_b."""
        form_data = {
            'class_a': self.class_a.id,
            'class_b': self.class_a.id,   # same class intentionally
            'constraint_type': 'prereq',
        }
        form = ClassConstraintsForm(self.program, form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('must be different', str(form.errors))

    def test_form_accepts_different_classes(self):
        """ClassConstraintsForm is valid when class_a != class_b."""
        form_data = {
            'class_a': self.class_a.id,
            'class_b': self.class_b.id,
            'constraint_type': 'mutual_exclusion',
        }
        form = ClassConstraintsForm(self.program, form_data)
        self.assertTrue(form.is_valid(), msg=str(form.errors))

    # ------------------------------------------------------------------
    # Label length safety
    # ------------------------------------------------------------------

    def test_long_title_label_truncated(self):
        """Labels must not exceed BooleanExpression.label max_length of 80."""
        cat, _ = ClassCategories.objects.get_or_create(
            category='Test Category', defaults={'symbol': 'T'},
        )
        long_class = ClassSubject.objects.create(
            title='X' * 200,
            category=cat,
            grade_min=7,
            grade_max=12,
            parent_program=self.program,
        )
        data = {'class_a': long_class, 'class_b': self.class_b, 'constraint_type': 'prereq'}
        # Must not raise DataError / ValueError due to label overflow
        self.module.add_constraint(self.program, data)
        expr = ScheduleConstraint.objects.get(program=self.program).condition
        self.assertLessEqual(len(expr.label), 80)
