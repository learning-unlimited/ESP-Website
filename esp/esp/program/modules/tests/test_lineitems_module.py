"""
Tests for esp.program.modules.handlers.lineitemsmodule
Source: esp/esp/program/modules/handlers/lineitemsmodule.py
"""
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule
from esp.program.modules.handlers.lineitemsmodule import LineItemsModule
from esp.program.modules.admin_search import AdminSearchEntry
from esp.accounting.models import LineItemType
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator',
                 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class LineItemsModuleAdminSearchTest(TestCase):
    """Tests for get_admin_search_entry classmethod."""

    def test_wrong_view_name_returns_none(self):
        """get_admin_search_entry should return None for non-matching view names."""
        result = LineItemsModule.get_admin_search_entry(
            None, None, "wrongview", None
        )
        self.assertIsNone(result)

    def test_correct_view_name_returns_admin_search_entry(self):
        """get_admin_search_entry should return AdminSearchEntry for 'lineitems'."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = LineItemsModule.get_admin_search_entry(
            program, None, "lineitems", None
        )
        self.assertIsInstance(result, AdminSearchEntry)

    def test_correct_view_name_returns_correct_id(self):
        """get_admin_search_entry should return entry with id 'manage_lineitems'."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = LineItemsModule.get_admin_search_entry(
            program, None, "lineitems", None
        )
        self.assertEqual(result.id, "manage_lineitems")

    def test_correct_view_name_returns_correct_url(self):
        """get_admin_search_entry should return correct management URL."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = LineItemsModule.get_admin_search_entry(
            program, None, "lineitems", None
        )
        self.assertEqual(result.url, "/manage/test/program/lineitems")

    def test_correct_view_name_returns_correct_category(self):
        """get_admin_search_entry should return entry in 'Configure' category."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = LineItemsModule.get_admin_search_entry(
            program, None, "lineitems", None
        )
        self.assertEqual(result.category, "Configure")

    def test_correct_view_name_returns_correct_keywords(self):
        """get_admin_search_entry should include relevant financial keywords."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = LineItemsModule.get_admin_search_entry(
            program, None, "lineitems", None
        )
        self.assertIn("fees", result.keywords)
        self.assertIn("payments", result.keywords)


class LineItemsModuleIsCompletedTest(TestCase):
    """Tests for isCompleted method."""

    def setUp(self):
        super().setUp()
        _setup_roles()

    def test_is_completed_false_when_no_lineitems(self):
        """isCompleted should return False when no line items exist."""
        module = LineItemsModule()
        mock_program = MagicMock()
        mock_program.lineitemtype_set.exclude.return_value.exists.return_value = False
        with patch.object(LineItemsModule, 'program', mock_program):
            self.assertFalse(module.isCompleted())

    def test_is_completed_true_when_lineitems_exist(self):
        """isCompleted should return True when line items exist."""
        module = LineItemsModule()
        mock_program = MagicMock()
        mock_program.lineitemtype_set.exclude.return_value.exists.return_value = True
        with patch.object(LineItemsModule, 'program', mock_program):
            self.assertTrue(module.isCompleted())

    def test_is_completed_returns_boolean(self):
        """isCompleted should always return a boolean value."""
        module = LineItemsModule()
        mock_program = MagicMock()
        mock_program.lineitemtype_set.exclude.return_value.exists.return_value = False
        with patch.object(LineItemsModule, 'program', mock_program):
            result = module.isCompleted()
            self.assertIsInstance(result, bool)


class LineItemsModuleIsStepTest(TestCase):
    """Tests for isStep method."""

    def setUp(self):
        super().setUp()
        _setup_roles()

    def test_is_step_false_when_no_student_extra_costs_module(self):
        """isStep should return False when program doesn't have StudentExtraCosts."""
        module = LineItemsModule()
        mock_program = MagicMock()
        mock_program.hasModule.return_value = False
        with patch.object(LineItemsModule, 'program', mock_program):
            self.assertFalse(module.isStep())

    def test_is_step_true_when_student_extra_costs_module_exists(self):
        """isStep should return True when program has StudentExtraCosts module."""
        module = LineItemsModule()
        mock_program = MagicMock()
        mock_program.hasModule.return_value = True
        with patch.object(LineItemsModule, 'program', mock_program):
            self.assertTrue(module.isStep())

    def test_is_step_checks_correct_module_name(self):
        """isStep should check for StudentExtraCosts specifically."""
        module = LineItemsModule()
        mock_program = MagicMock()
        mock_program.hasModule.return_value = False
        with patch.object(LineItemsModule, 'program', mock_program):
            module.isStep()
            mock_program.hasModule.assert_called_once_with("StudentExtraCosts")


class LineItemsModulePropertiesTest(TestCase):
    """Tests for module_properties classmethod."""

    def test_module_properties_returns_dict(self):
        """module_properties should return a dictionary."""
        props = LineItemsModule.module_properties()
        self.assertIsInstance(props, dict)

    def test_module_properties_has_required_keys(self):
        """module_properties should contain all required keys."""
        props = LineItemsModule.module_properties()
        self.assertIn("admin_title", props)
        self.assertIn("link_title", props)
        self.assertIn("module_type", props)

    def test_module_properties_is_manage_type(self):
        """LineItemsModule should be a manage-type module."""
        props = LineItemsModule.module_properties()
        self.assertEqual(props["module_type"], "manage")

    def test_module_has_correct_admin_title(self):
        """LineItemsModule should have correct admin title."""
        props = LineItemsModule.module_properties()
        self.assertEqual(props["admin_title"], "Line Items Module")

    def test_setup_title_exists(self):
        """LineItemsModule should have a setup_title defined."""
        self.assertTrue(hasattr(LineItemsModule, 'setup_title'))
        self.assertIsInstance(LineItemsModule.setup_title, str)


class LineItemsModuleViewTest(ProgramFrameworkTest):
    """View-level tests for LineItemsModule using real HTTP requests."""

    def setUp(self):
        modules = [
            ProgramModule.objects.get(handler='LineItemsModule'),
            ProgramModule.objects.get(handler='AdminCore'),
        ]
        super().setUp(modules=modules)

        self.adminUser, created = ESPUser.objects.get_or_create(
            username='lineitemsadmin'
        )
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()

        self.student = self.students[0]
        self.student.set_password('password')
        self.student.save()

        self.url = '/manage/' + self.program.url + '/lineitems'

    def test_admin_can_access_lineitems_view(self):
        """Admin users should get 200 response from lineitems view."""
        self.client.login(username='lineitemsadmin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_access_lineitems_view(self):
        """Non-admin users should not see line items management content."""
        self.client.login(username=self.student.username,password='password')
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Line Items Management', status_code=response.status_code)

    def test_unauthenticated_user_redirected(self):
        """Unauthenticated users should be redirected from lineitems view."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_lineitems_view_contains_program_in_context(self):
        """Lineitems view should include program in context."""
        self.client.login(username='lineitemsadmin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('prog', response.context)

    def test_get_delete_shows_confirmation(self):
        """GET with op=delete should show delete confirmation page."""
        self.client.login(username='lineitemsadmin', password='password')
        lineitem = LineItemType.objects.create(
            text='Test Item',
            amount_dec=10.00,
            program=self.program,
            required=False,
        )
        response = self.client.get(
            self.url + '?op=delete&id=' + str(lineitem.id)
        )
        self.assertEqual(response.status_code, 200)

    def test_post_delete_removes_lineitem(self):
        """POST with command=reallyremove should delete the line item."""
        self.client.login(username='lineitemsadmin', password='password')
        lineitem = LineItemType.objects.create(
            text='Delete Me',
            amount_dec=5.00,
            program=self.program,
            required=False,
        )
        lineitem_id = lineitem.id
        self.client.post(self.url, {
            'command': 'reallyremove',
            'id': lineitem_id,
        })
        self.assertFalse(
            LineItemType.objects.filter(id=lineitem_id).exists()
        )

    def test_lineitems_view_shows_existing_lineitems(self):
        """Lineitems view should list existing line items in context."""
        self.client.login(username='lineitemsadmin', password='password')
        LineItemType.objects.create(
            text='Visible Item',
            amount_dec=20.00,
            program=self.program,
            required=False,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('lineitems', response.context)

    def test_get_edit_loads_lineitem_form(self):
        """GET with op=edit should load the line item form with correct instance."""
        self.client.login(username='lineitemsadmin', password='password')
        lineitem = LineItemType.objects.create(
            text='Edit Me',
            amount_dec=15.00,
            program=self.program,
            required=False,
        )
        response = self.client.get(
            self.url + '?op=edit&id=' + str(lineitem.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('lineitem_form', response.context)
        self.assertIn('lineitem', response.context)
        self.assertEqual(response.context['lineitem'].id, lineitem.id)