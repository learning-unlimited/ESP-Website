from django.core.exceptions import ValidationError
from django.test import TestCase
from esp.program.models import Program


class ProgramValidationTest(TestCase):

    def test_invalid_grade_range(self):
        program = Program(grade_min=10, grade_max=5)

        with self.assertRaises(ValidationError):
            program.full_clean()

    def test_negative_grade(self):
        program = Program(grade_min=-1, grade_max=5)

        with self.assertRaises(ValidationError):
            program.full_clean()
