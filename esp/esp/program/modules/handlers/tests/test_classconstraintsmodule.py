"""
Tests for ClassConstraintsModule and ScheduleTestSubject.
"""
import logging

from esp.program.controllers.lunch_constraints import LunchConstraintGenerator
from esp.program.models import (
    BooleanExpression, BooleanToken, ClassCategories,
    Program, ScheduleConstraint, ScheduleMap, ScheduleTestSubject,
)
from esp.program.models.class_ import ClassSection, ClassSubject
from esp.program.modules.base import CoreModule, ProgramModuleObj
from esp.program.modules.forms.admincore import LunchConstraintsForm
from esp.program.modules.handlers.admincore import AdminCore
from esp.program.modules.handlers.classconstraintsmodule import (
    ClassConstraintsForm,
    ClassConstraintsModule,
)
from esp.program.tests import ProgramFrameworkTest
from esp.tests.util import CacheFlushTestCase, user_role_setup


class ClassConstraintsModuleTest(CacheFlushTestCase):
    """Tests for ClassConstraintsModule constraint creation and evaluation."""

    def setUp(self):
        super().setUp()
        logging.disable(logging.CRITICAL)
        user_role_setup()

        self.program = Program.objects.create(
            name="Test Program",
            url="testprog/test",
            grade_min=7,
            grade_max=12,
        )

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

    def _add(self, constraint_type, class_a=None, class_b=None):
        self.module.add_constraint(self.program, {
            'class_a': class_a or self.class_a,
            'class_b': class_b or self.class_b,
            'constraint_type': constraint_type,
        })
        return ScheduleConstraint.objects.get(program=self.program)

    # ------------------------------------------------------------------
    # Constraint creation
    # ------------------------------------------------------------------

    def test_add_requires_constraint(self):
        """add_constraint creates one ScheduleConstraint with the correct tokens."""
        constraint = self._add('requires')

        # Labels complete "... requires that you <label>" in student-facing errors
        self.assertEqual(constraint.condition.label, f"take {self.class_a.emailcode()}: Class A")
        self.assertEqual(constraint.requirement.label, f"also take {self.class_b.emailcode()}: Class B")

        # on_failure is no longer executed, so it is left empty
        self.assertEqual(constraint.on_failure, '')

        # Condition token -> subject A
        cond_tokens = constraint.condition.get_stack()
        self.assertEqual(len(cond_tokens), 1)
        self.assertIsInstance(cond_tokens[0], ScheduleTestSubject)
        self.assertEqual(cond_tokens[0].subject_id, self.class_a.id)

        # Requirement token -> subject B
        req_tokens = constraint.requirement.get_stack()
        self.assertEqual(len(req_tokens), 1)
        self.assertEqual(req_tokens[0].subject_id, self.class_b.id)

    def test_add_mutual_exclusion_constraint(self):
        """Mutual exclusion creates IF enrolled(A) THEN NOT enrolled(B)."""
        constraint = self._add('mutual_exclusion')
        self.assertEqual(constraint.requirement.label, f"not take {self.class_b.emailcode()}: Class B")

        req_tokens = constraint.requirement.get_stack()
        # Stack (ordered by seq): [ScheduleTestSubject(B) seq=0, BooleanToken("NOT") seq=10]
        self.assertEqual(len(req_tokens), 2)
        self.assertIsInstance(req_tokens[0], ScheduleTestSubject)
        self.assertEqual(req_tokens[0].subject_id, self.class_b.id)
        self.assertIsInstance(req_tokens[1], BooleanToken)
        self.assertEqual(req_tokens[1].text, "NOT")

    # ------------------------------------------------------------------
    # Constraint evaluation
    # ------------------------------------------------------------------

    def test_evaluate_requires(self):
        """
        Evaluate the expressions against dicts shaped like ScheduleMap.map
        (timeslot id -> list of ClassSections), which is what
        ScheduleTestSubject.boolean_value receives as kwargs['map'].
        """
        constraint = self._add('requires')

        sec_a = ClassSection.objects.create(parent_class=self.class_a)
        sec_b = ClassSection.objects.create(parent_class=self.class_b)

        smap_a_only = {1: [sec_a]}
        smap_both   = {1: [sec_a, sec_b]}
        smap_b_only = {1: [sec_b]}

        # Token correctly identifies enrollment
        cond_token = constraint.condition.get_stack()[0]
        self.assertTrue(cond_token.boolean_value(map=smap_a_only))
        self.assertFalse(cond_token.boolean_value(map=smap_b_only))

        # Case 1: Only in A -> condition satisfied, requirement not
        self.assertTrue(constraint.condition.evaluate(map=smap_a_only))
        self.assertFalse(constraint.requirement.evaluate(map=smap_a_only))

        # Case 2: In A and B -> both satisfied
        self.assertTrue(constraint.condition.evaluate(map=smap_both))
        self.assertTrue(constraint.requirement.evaluate(map=smap_both))

        # Case 3: Only in B -> condition not satisfied (constraint irrelevant)
        self.assertFalse(constraint.condition.evaluate(map=smap_b_only))

    def test_boolean_value_map_none_is_safe(self):
        """boolean_value must not raise when map kwarg is None or missing."""
        token = ScheduleTestSubject(subject=self.class_a)
        self.assertFalse(token.boolean_value(map=None))
        self.assertFalse(token.boolean_value())

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def test_delete_constraint_removes_orphaned_expressions(self):
        """Deleting a constraint also removes its expressions if unreferenced."""
        constraint = self._add('requires')
        cond_id = constraint.condition_id
        req_id = constraint.requirement_id

        self.module._delete_constraint(constraint.id, self.program)

        self.assertFalse(ScheduleConstraint.objects.filter(id=constraint.id).exists())
        self.assertFalse(BooleanExpression.objects.filter(id=cond_id).exists())
        self.assertFalse(BooleanExpression.objects.filter(id=req_id).exists())

    def test_delete_leaves_shared_expression_intact(self):
        """If an expression is shared across constraints, only the constraint is removed."""
        shared_expr = BooleanExpression.objects.create(label="shared")
        req_a = BooleanExpression.objects.create(label="req_a")
        req_b = BooleanExpression.objects.create(label="req_b")

        # Only constraints whose condition has a ScheduleTestSubject belong to this module
        ScheduleTestSubject.objects.create(exp=shared_expr, subject=self.class_a)

        c1 = ScheduleConstraint.objects.create(
            program=self.program, condition=shared_expr, requirement=req_a, on_failure=''
        )
        c2 = ScheduleConstraint.objects.create(
            program=self.program, condition=shared_expr, requirement=req_b, on_failure=''
        )

        self.module._delete_constraint(c1.id, self.program)

        # shared_expr is still referenced by c2, so it must survive
        self.assertTrue(BooleanExpression.objects.filter(id=shared_expr.id).exists())
        self.assertTrue(ScheduleConstraint.objects.filter(id=c2.id).exists())
        # The unreferenced req_a should be gone
        self.assertFalse(BooleanExpression.objects.filter(id=req_a.id).exists())

    def test_delete_ignores_other_constraints(self):
        """The delete action cannot remove constraints this module did not create."""
        other = ScheduleConstraint.objects.create(
            program=self.program,
            condition=BooleanExpression.objects.create(label="lunch check"),
            requirement=BooleanExpression.objects.create(label="choose a lunch period"),
            on_failure='',
        )
        self.module._delete_constraint(other.id, self.program)
        self.assertTrue(ScheduleConstraint.objects.filter(id=other.id).exists())

    def test_deleting_class_removes_its_constraints(self):
        """Deleting either class removes the constraint and its expressions."""
        for constraint_type, deleted in [('requires', 1), ('mutual_exclusion', 1), ('requires', 0)]:
            with self.subTest(constraint_type=constraint_type, deleted=deleted):
                classes = [
                    ClassSubject.objects.create(title=f"Class {i}", category=self.class_a.category,
                                                grade_min=7, grade_max=12, parent_program=self.program)
                    for i in range(2)
                ]
                constraint = self._add(constraint_type, *classes)
                exp_ids = [constraint.condition_id, constraint.requirement_id]

                classes[deleted].delete()

                self.assertFalse(ScheduleConstraint.objects.filter(id=constraint.id).exists())
                self.assertFalse(BooleanExpression.objects.filter(id__in=exp_ids).exists())
                self.assertFalse(BooleanToken.objects.filter(exp_id__in=exp_ids).exists())

    def test_lunch_constraints_leave_class_constraints_alone(self):
        """Regenerating lunch constraints must not delete class constraints."""
        constraint = self._add('requires')
        lunch = ScheduleConstraint.objects.create(
            program=self.program,
            condition=BooleanExpression.objects.create(label="lunch check"),
            requirement=BooleanExpression.objects.create(label="choose a lunch period"),
            on_failure='',
        )

        LunchConstraintGenerator(self.program, []).clear_existing_constraints()

        self.assertTrue(ScheduleConstraint.objects.filter(id=constraint.id).exists())
        self.assertFalse(ScheduleConstraint.objects.filter(id=lunch.id).exists())

    def test_lunch_form_ignores_class_constraints(self):
        """Class constraints must not make the lunch form look configured."""
        self._add('requires')
        form = LunchConstraintsForm(self.program)
        self.assertFalse(form.fields['generate_constraints'].initial)

    # ------------------------------------------------------------------
    # Form validation
    # ------------------------------------------------------------------

    def test_form_rejects_same_class_for_a_and_b(self):
        """ClassConstraintsForm.clean() must reject class_a == class_b."""
        form_data = {
            'class_a': self.class_a.id,
            'class_b': self.class_a.id,   # same class intentionally
            'constraint_type': 'requires',
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

    def test_form_rejects_class_from_other_program(self):
        """Class choices are limited to the current program."""
        other_program = Program.objects.create(name="Other", url="other/test", grade_min=7, grade_max=12)
        other_class = ClassSubject.objects.create(
            title="Elsewhere", category=self.class_a.category, grade_min=7, grade_max=12,
            parent_program=other_program,
        )
        form = ClassConstraintsForm(self.program, {
            'class_a': self.class_a.id,
            'class_b': other_class.id,
            'constraint_type': 'requires',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('class_b', form.errors)

    # ------------------------------------------------------------------
    # Label length safety
    # ------------------------------------------------------------------

    def test_long_title_label_truncated(self):
        """Labels must not exceed BooleanExpression.label max_length of 80."""
        long_class = ClassSubject.objects.create(
            title='X' * 200,
            category=self.class_a.category,
            grade_min=7,
            grade_max=12,
            parent_program=self.program,
        )
        expr = self._add('requires', class_a=long_class).condition
        self.assertEqual(len(expr.label), 80)
        self.assertTrue(expr.label.startswith(f"take {long_class.emailcode()}: "))

    # ------------------------------------------------------------------
    # Module registration
    # ------------------------------------------------------------------

    def test_module_is_not_core(self):
        """getCoreURL() returns the first CoreModule, which must stay AdminCore."""
        self.assertFalse(issubclass(ClassConstraintsModule, CoreModule))


class ClassConstraintsIntegrationTest(ProgramFrameworkTest):
    """End-to-end tests through the management page and registration checks."""

    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        self.student = self.students[0]
        self.client.login(username=self.admin.username, password='password')
        self.url = f'/manage/{self.program.getUrlBase()}/class_constraints'

        # Two classes in different timeblocks, so they don't conflict
        timeslots = list(self.program.getTimeSlots())
        self.subjects = list(self.program.classes().order_by('id')[:2])
        self.sections = []
        for subject, timeslot in zip(self.subjects, timeslots):
            section = subject.get_sections()[0]
            section.assign_start_time(timeslot)
            self.sections.append(section)

    def _post_add(self, constraint_type):
        return self.client.post(self.url, {
            'add': '',
            'class_a': self.subjects[0].id,
            'class_b': self.subjects[1].id,
            'constraint_type': constraint_type,
        })

    def test_main_management_page_still_served_by_admincore(self):
        """Enabling this module must not take over /manage/<program>/main."""
        self.assertIsInstance(ProgramModuleObj.findModuleObject('manage', 'main', self.program), AdminCore)
        self.assertIsInstance(ProgramModuleObj.findModuleObject('manage', 'class_constraints', self.program), ClassConstraintsModule)

    def test_page_requires_admin(self):
        self.client.logout()
        self.client.login(username=self.student.username, password='password')
        response = self._post_add('requires')
        self.assertTemplateUsed(response, 'errors/program/notanadmin.html')
        self.assertFalse(ScheduleConstraint.objects.filter(program=self.program).exists())

    def test_add_list_and_delete_via_page(self):
        response = self._post_add('requires')
        self.assertEqual(response.status_code, 302)
        constraint = ScheduleConstraint.objects.get(program=self.program)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Students who {constraint.condition.label} must {constraint.requirement.label}")

        response = self.client.post(self.url, {'delete': '', 'constraint_id': constraint.id})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ScheduleConstraint.objects.filter(program=self.program).exists())

    def test_delete_with_invalid_id_returns_400(self):
        response = self.client.post(self.url, {'delete': '', 'constraint_id': 'abc'})
        self.assertEqual(response.status_code, 400)

    def test_requires_blocks_adding_class_a_alone(self):
        self._post_add('requires')
        message = self.sections[0].cannotAdd(self.student)
        self.assertIn(f"requires that you also take {self.subjects[1].emailcode()}", message)

        # Once enrolled in B, the constraint is satisfied
        smap = ScheduleMap(self.student, self.program)
        smap.add_section(self.sections[1])
        smap.add_section(self.sections[0])
        self.assertTrue(ScheduleConstraint.objects.get(program=self.program).evaluate(smap))

    def test_mutual_exclusion_blocks_both_orders(self):
        self._post_add('mutual_exclusion')
        constraint = ScheduleConstraint.objects.get(program=self.program)
        for first, second in [(0, 1), (1, 0)]:
            smap = ScheduleMap(self.student, self.program)
            smap.add_section(self.sections[first])
            self.assertTrue(constraint.evaluate(smap))
            smap.add_section(self.sections[second])
            self.assertFalse(constraint.evaluate(smap))
