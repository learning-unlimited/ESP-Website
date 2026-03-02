from esp.program.modules.handlers.formstackappmodule import (
    resolve_field_expression
)
from esp.program.tests import ProgramFrameworkTest


class FormstackAppModuleTest(ProgramFrameworkTest):
    def test_resolve_valid_expression(self):
        """Valid user attribute expressions resolve correctly."""
        user = self.students[0]
        context = {'user': user}
        result = resolve_field_expression('user.username', context)
        self.assertEqual(result, user.username)

    def test_resolve_invalid_expression(self):
        """Invalid expressions return None instead of raising."""
        user = self.students[0]
        context = {'user': user}
        result = resolve_field_expression(
            'user.nonexistent_field_xyz', context
        )
        self.assertIsNone(result)

    def test_resolve_malformed_expression(self):
        """Malformed expressions return None instead of 500ing."""
        user = self.students[0]
        result = resolve_field_expression('', {'user': user})
        self.assertIsNone(result)

    def test_resolve_empty_string_value(self):
        """Expressions resolving to empty string return '' not None."""
        user = self.students[0]
        # Patch a field to be empty to verify empty string is preserved
        original = user.username
        user.username = ''
        context = {'user': user}
        result = resolve_field_expression('user.username', context)
        self.assertEqual(result, '')
        user.username = original
