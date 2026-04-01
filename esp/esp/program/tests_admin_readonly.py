from django.test import RequestFactory

from esp.admin import admin_site
from esp.program.admin import ProgramModuleAdmin, Admin_ClassCategories
from esp.program.models import ProgramModule, ClassCategories
from esp.tests.util import CacheFlushTestCase as TestCase


class AdminReadonlyFieldsTest(TestCase):
    def setUp(self):
        self.request = RequestFactory().get('/')

    def test_program_module_fields_edit_only(self):
        admin = ProgramModuleAdmin(ProgramModule, admin_site)

        create_fields = admin.get_readonly_fields(self.request, obj=None)
        edit_fields = admin.get_readonly_fields(self.request, obj=object())

        self.assertNotIn('handler', create_fields)
        self.assertNotIn('module_type', create_fields)
        self.assertIn('handler', edit_fields)
        self.assertIn('module_type', edit_fields)

    def test_class_categories_symbol_edit_only(self):
        admin = Admin_ClassCategories(ClassCategories, admin_site)

        create_fields = admin.get_readonly_fields(self.request, obj=None)
        edit_fields = admin.get_readonly_fields(self.request, obj=object())

        self.assertNotIn('symbol', create_fields)
        self.assertIn('symbol', edit_fields)
