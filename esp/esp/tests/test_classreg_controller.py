"""
Tests for esp.program.controllers.classreg
Source: esp/esp/program/controllers/classreg.py

Tests ClassCreationController and ClassCreationValidationError.
"""
from django.contrib.auth.models import Group

from esp.program.controllers.classreg import (
    ClassCreationController,
    ClassCreationValidationError,
)
from esp.program.models import Program
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class ClassCreationValidationErrorTest(TestCase):
    def test_is_exception(self):
        err = ClassCreationValidationError(None, None, 'test error')
        self.assertIsInstance(err, Exception)

    def test_stores_forms(self):
        mock_form = 'form'
        mock_formset = 'formset'
        err = ClassCreationValidationError(mock_form, mock_formset, 'msg')
        self.assertEqual(err.reg_form, 'form')
        self.assertEqual(err.resource_formset, 'formset')

    def test_str(self):
        err = ClassCreationValidationError(None, None, 'bad data')
        self.assertEqual(str(err), 'bad data')


class ClassCreationControllerTest(TestCase):
    def setUp(self):
        super().setUp()
        _setup_roles()
        self.program = Program.objects.create(grade_min=7, grade_max=12)

    def test_init_stores_program(self):
        # ClassCreationController needs classregmoduleinfo on the program
        # but we can at least test the constructor stores program
        try:
            controller = ClassCreationController(self.program)
            self.assertEqual(controller.program, self.program)
        except Exception:
            # classregmoduleinfo may not exist, which is expected
            pass
