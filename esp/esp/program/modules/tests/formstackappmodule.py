from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest


class FormstackAppModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.program.getModules()
        pm = ProgramModule.objects.get(handler='FormstackAppModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

    def test_resolve_valid_expression(self):
        """Valid user attribute expressions resolve correctly."""
        user = self.students[0]
        result = self.module._resolve_field_expression('user.username', {'user': user})
        self.assertEqual(result, user.username)

    def test_resolve_invalid_expression(self):
        """Invalid expressions return None instead of raising."""
        user = self.students[0]
        result = self.module._resolve_field_expression('user.nonexistent_field_xyz', {'user': user})
        self.assertIsNone(result)

    def test_resolve_malformed_expression(self):
        """Malformed expressions return None instead of 500ing."""
        user = self.students[0]
        result = self.module._resolve_field_expression('', {'user': user})
        self.assertIsNone(result)

    def test_resolve_empty_string_value(self):
        """Expressions resolving to empty string return '' not None."""
        user = self.students[0]
        # Patch a field to be empty to verify empty string is preserved
        original = user.username
        user.username = ''
        result = self.module._resolve_field_expression('user.username', {'user': user})
        self.assertEqual(result, '')
        user.username = original
