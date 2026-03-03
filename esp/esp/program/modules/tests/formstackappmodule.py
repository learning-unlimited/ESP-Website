from esp.program.modules.handlers.formstackappmodule import (
    resolve_field_expression
)
from esp.program.tests import ProgramFrameworkTest


class FormstackAppModuleTest(ProgramFrameworkTest):
    """Tests for the resolve_field_expression helper."""

    def test_resolve_valid_expression(self):
        """Valid dotted attribute expressions resolve correctly."""
        user = self.students[0]
        result = resolve_field_expression('user.username', {'user': user})
        self.assertEqual(result, user.username)

    def test_resolve_invalid_expression(self):
        """Unknown attributes return None instead of raising."""
        result = resolve_field_expression(
            'user.nonexistent_field_xyz', {'user': self.students[0]}
        )
        self.assertIsNone(result)

    def test_resolve_empty_expression(self):
        """Empty string expressions return None instead of raising."""
        result = resolve_field_expression('', {'user': self.students[0]})
        self.assertIsNone(result)

    def test_resolve_whitespace_expression(self):
        """Whitespace-only expressions return None."""
        result = resolve_field_expression('   ', {'user': self.students[0]})
        self.assertIsNone(result)

    def test_resolve_leading_trailing_whitespace(self):
        """Leading/trailing whitespace around expressions is stripped."""
        user = self.students[0]
        result = resolve_field_expression('  user.username  ', {'user': user})
        self.assertEqual(result, user.username)

    def test_resolve_expression_with_leading_whitespace(self):
        """Expressions with leading whitespace (e.g. from '123: user.username') resolve correctly."""
        user = self.students[0]
        result = resolve_field_expression(' user.username', {'user': user})
        self.assertEqual(result, user.username)

    def test_resolve_empty_string_value(self):
        """Expressions resolving to empty string return '' not None."""
        user = self.students[0]
        original = user.username
        try:
            user.username = ''
            context = {'user': user}
            result = resolve_field_expression('user.username', context)
            self.assertEqual(result, '')
        finally:
            user.username = original

    def test_resolve_none_value(self):
        """Expressions resolving to None return None, not 'None' string."""
        context = {'user': None}
        result = resolve_field_expression('user', context)
        self.assertIsNone(result)
