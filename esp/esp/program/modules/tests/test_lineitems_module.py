from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.handlers.lineitemsmodule import LineItemsModule
from esp.program.modules.admin_search import AdminSearchEntry
from esp.tests.util import CacheFlushTestCase as TestCase

class LineItemsModuleAdminSearchTest(TestCase):

    def test_get_admin_search_entry_wrong_view_returns_none(self):
        result = LineItemsModule.get_admin_search_entry(
            None, None, 'wrongview', None
        )
        self.assertIsNone(result)

class LineItemsModuleTest(ProgramFrameworkTest):

    def test_get_admin_search_entry_correct_view_returns_entry(self):
        result = LineItemsModule.get_admin_search_entry(
            self.program, None, 'lineitems', None
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, AdminSearchEntry)
        self.assertEqual(result.id, 'manage_lineitems')

    def test_get_admin_search_entry_has_correct_keywords(self):
        result = LineItemsModule.get_admin_search_entry(
            self.program, None, 'lineitems', None
        )
        self.assertIn('fees', result.keywords)
