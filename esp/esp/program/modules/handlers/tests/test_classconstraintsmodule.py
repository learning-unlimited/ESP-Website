import logging
from django.test import TestCase
from esp.program.models import Program, ClassSubject, ScheduleConstraint, BooleanExpression, BooleanToken, ScheduleTestSubject
from esp.program.modules.handlers.classconstraintsmodule import ClassConstraintsModule
from esp.program.models.class_ import ClassSection

class ClassConstraintsModuleTest(TestCase):
    def setUp(self):
        # Disable logging to keep test output clean
        logging.disable(logging.CRITICAL)
        
        self.program = Program.objects.create(name="Test Program", url="testprog", program_type="test", program_instance="test")
        self.class_a = ClassSubject.objects.create(title="Class A", parent_program=self.program)
        self.class_b = ClassSubject.objects.create(title="Class B", parent_program=self.program)
        
        self.module = ClassConstraintsModule()
        self.module.program = self.program

    def test_add_prereq_constraint(self):
        data = {
            'class_a': self.class_a,
            'class_b': self.class_b,
            'constraint_type': 'prereq'
        }
        self.module.add_constraint(self.program, data)
        
        constraints = ScheduleConstraint.objects.filter(program=self.program)
        self.assertEqual(constraints.count(), 1)
        constraint = constraints[0]
        
        self.assertIn("Enrolled in Class A", constraint.condition.label)
        self.assertIn("Enrolled in Class B", constraint.requirement.label)
        
        cond_tokens = constraint.condition.get_stack()
        self.assertEqual(len(cond_tokens), 1)
        self.assertEqual(cond_tokens[0].subclass_instance().subject, self.class_a)
        
        req_tokens = constraint.requirement.get_stack()
        self.assertEqual(len(req_tokens), 1)
        self.assertEqual(req_tokens[0].subclass_instance().subject, self.class_b)

    def test_add_mutual_exclusion_constraint(self):
        data = {
            'class_a': self.class_a,
            'class_b': self.class_b,
            'constraint_type': 'mutual_exclusion'
        }
        self.module.add_constraint(self.program, data)
        
        constraints = ScheduleConstraint.objects.filter(program=self.program)
        self.assertEqual(constraints.count(), 1)
        constraint = constraints[0]
        
        req_tokens = constraint.requirement.get_stack()
        # NOT in Class B: [ScheduleTestSubject(B), BooleanToken(NOT)]
        self.assertEqual(len(req_tokens), 2)
        self.assertEqual(req_tokens[0].subclass_instance().subject, self.class_b)
        self.assertEqual(req_tokens[1].text, "NOT")

    def test_evaluate_constraint(self):
        # IF A THEN B
        data = {
            'class_a': self.class_a,
            'class_b': self.class_b,
            'constraint_type': 'prereq'
        }
        self.module.add_constraint(self.program, data)
        constraint = ScheduleConstraint.objects.get(program=self.program)
        
        # Setup sections
        sec_a = ClassSection.objects.create(parent_class=self.class_a)
        sec_b = ClassSection.objects.create(parent_class=self.class_b)
        
        # Case 1: Only in A -> should fail (Condition True, Requirement False)
        smap1 = {1: [sec_a]}
        self.assertTrue(constraint.condition.evaluate(map=smap1))
        self.assertFalse(constraint.requirement.evaluate(map=smap1))
        
        # Case 2: In A and B -> should pass
        smap2 = {1: [sec_a, sec_b]}
        self.assertTrue(constraint.condition.evaluate(map=smap2))
        self.assertTrue(constraint.requirement.evaluate(map=smap2))
        
        # Case 3: Only in B -> should pass (Condition False, constraint not applicable)
        smap3 = {1: [sec_b]}
        self.assertFalse(constraint.condition.evaluate(map=smap3))

    def tearDown(self):
        logging.disable(logging.NOTSET)
