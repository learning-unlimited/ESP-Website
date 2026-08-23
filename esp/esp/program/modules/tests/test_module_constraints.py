from importlib import import_module
from unittest import TestCase


class ModuleConstraintRulesTest(TestCase):
    def _constraint_module(self):
        try:
            return import_module('esp.program.modules.module_constraints')
        except ModuleNotFoundError as exc:
            if exc.name == 'esp.program.modules.module_constraints':
                self.fail('Module constraint rules must live in a shared module')
            raise

    def test_constraint_metadata_for_each_locked_module_family(self):
        constraint_module = self._constraint_module()
        cases = (
            (
                'StudentRegProfileModule',
                {
                    'required_locked': True,
                    'not_required_locked': False,
                    'position_locked': True,
                },
            ),
            (
                'TeacherRegProfileModule',
                {
                    'required_locked': True,
                    'not_required_locked': False,
                    'position_locked': True,
                },
            ),
            (
                'AvailabilityModule',
                {
                    'required_locked': True,
                    'not_required_locked': False,
                    'position_locked': False,
                },
            ),
            (
                'StudentAcknowledgementModule',
                {
                    'required_locked': True,
                    'not_required_locked': False,
                    'position_locked': False,
                },
            ),
            (
                'StudentRegTwoPhase',
                {
                    'required_locked': True,
                    'not_required_locked': False,
                    'position_locked': False,
                },
            ),
            (
                'CreditCardModule_Stripe',
                {
                    'required_locked': False,
                    'not_required_locked': True,
                    'position_locked': True,
                },
            ),
            (
                'StudentRegConfirm',
                {
                    'required_locked': False,
                    'not_required_locked': True,
                    'position_locked': True,
                },
            ),
        )

        for handler, expected in cases:
            with self.subTest(handler=handler):
                self.assertEqual(
                    constraint_module.get_module_constraints(handler),
                    expected,
                )

    def test_unconstrained_handler_has_no_metadata(self):
        constraint_module = self._constraint_module()

        self.assertIsNone(
            constraint_module.get_module_constraints('StudentClassRegModule')
        )

    def test_enforcement_helper_is_shared(self):
        constraint_module = self._constraint_module()

        self.assertTrue(callable(constraint_module.enforce_module_constraints))
