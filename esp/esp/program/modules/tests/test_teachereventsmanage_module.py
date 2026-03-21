"""
Tests for esp.program.modules.handlers.teachereventsmanagemodule
Source: esp/esp/program/modules/handlers/teachereventsmanagemodule.py
"""
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule
from esp.program.modules.handlers.teachereventsmanagemodule import TeacherEventsManageModule
from esp.program.modules.admin_search import AdminSearchEntry
from esp.cal.models import Event, EventType
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator',
                 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class TeacherEventsManageModulePropertiesTest(TestCase):
    """Tests for module_properties classmethod."""

    def test_module_properties_returns_dict(self):
        """module_properties should return a dictionary."""
        props = TeacherEventsManageModule.module_properties()
        self.assertIsInstance(props, dict)

    def test_module_properties_has_required_keys(self):
        """module_properties should contain all required keys."""
        props = TeacherEventsManageModule.module_properties()
        self.assertIn("admin_title", props)
        self.assertIn("link_title", props)
        self.assertIn("module_type", props)
        self.assertIn("seq", props)
        self.assertIn("choosable", props)

    def test_module_properties_is_manage_type(self):
        """TeacherEventsManageModule should be a manage-type module."""
        props = TeacherEventsManageModule.module_properties()
        self.assertEqual(props["module_type"], "manage")

    def test_module_properties_correct_admin_title(self):
        """TeacherEventsManageModule should have correct admin title."""
        props = TeacherEventsManageModule.module_properties()
        self.assertEqual(props["admin_title"], "Manage Teacher Training and Interviews")

    def test_module_properties_correct_link_title(self):
        """TeacherEventsManageModule should have correct link title."""
        props = TeacherEventsManageModule.module_properties()
        self.assertEqual(props["link_title"], "Teacher Training and Interviews")

    def test_module_properties_not_required(self):
        """TeacherEventsManageModule should not be required."""
        props = TeacherEventsManageModule.module_properties()
        self.assertFalse(props["required"])

    def test_module_properties_not_choosable(self):
        """TeacherEventsManageModule should not be choosable."""
        props = TeacherEventsManageModule.module_properties()
        self.assertEqual(props["choosable"], 0)

    def test_setup_title_exists(self):
        """TeacherEventsManageModule should have a setup_title defined."""
        self.assertTrue(hasattr(TeacherEventsManageModule, 'setup_title'))
        self.assertIsInstance(TeacherEventsManageModule.setup_title, str)


class TeacherEventsManageModuleAdminSearchTest(TestCase):
    """Tests for get_admin_search_entry classmethod."""

    def test_wrong_view_name_returns_none(self):
        """get_admin_search_entry should return None for non-matching view names."""
        result = TeacherEventsManageModule.get_admin_search_entry(
            None, None, "wrongview", None
        )
        self.assertIsNone(result)

    def test_correct_view_name_returns_entry(self):
        """get_admin_search_entry should return AdminSearchEntry for 'teacher_events'."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = TeacherEventsManageModule.get_admin_search_entry(
            program, None, "teacher_events", None
        )
        self.assertIsInstance(result, AdminSearchEntry)

    def test_correct_view_name_returns_correct_id(self):
        """get_admin_search_entry should return entry with correct id."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = TeacherEventsManageModule.get_admin_search_entry(
            program, None, "teacher_events", None
        )
        self.assertEqual(result.id, "manage_teacher_events")

    def test_correct_view_name_returns_correct_url(self):
        """get_admin_search_entry should return correct management URL."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = TeacherEventsManageModule.get_admin_search_entry(
            program, None, "teacher_events", None
        )
        self.assertEqual(result.url, "/manage/test/program/teacher_events")

    def test_correct_view_name_returns_correct_category(self):
        """get_admin_search_entry should return entry in 'Configure' category."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = TeacherEventsManageModule.get_admin_search_entry(
            program, None, "teacher_events", None
        )
        self.assertEqual(result.category, "Configure")

    def test_correct_view_returns_correct_keywords(self):
        """get_admin_search_entry should include relevant keywords."""
        program = MagicMock()
        program.getUrlBase.return_value = "test/program"
        result = TeacherEventsManageModule.get_admin_search_entry(
            program, None, "teacher_events", None
        )
        self.assertIn("teacher", result.keywords)
        self.assertIn("training", result.keywords)
        self.assertIn("interviews", result.keywords)

    def test_multiple_wrong_view_names_return_none(self):
        """get_admin_search_entry should return None for any non-matching view name."""
        for view_name in ["lineitems", "manage", "dashboard", ""]:
            result = TeacherEventsManageModule.get_admin_search_entry(
                None, None, view_name, None
            )
            self.assertIsNone(result)


class TeacherEventsManageModuleIsStepTest(TestCase):
    """Tests for isStep method."""

    def test_is_step_always_returns_true(self):
        """isStep should always return True."""
        module = TeacherEventsManageModule()
        self.assertTrue(module.isStep())

    def test_is_step_returns_boolean(self):
        """isStep should return a boolean."""
        module = TeacherEventsManageModule()
        self.assertIsInstance(module.isStep(), bool)


class TeacherEventsManageModuleAvailabilityRoleTest(TestCase):
    """Tests for availability_role method."""

    def setUp(self):
        super().setUp()
        _setup_roles()

    def test_availability_role_returns_teacher_group(self):
        """availability_role should return the Teacher group."""
        module = TeacherEventsManageModule()
        role = module.availability_role()
        self.assertEqual(role.name, 'Teacher')

    def test_availability_role_returns_group_instance(self):
        """availability_role should return a Group instance."""
        module = TeacherEventsManageModule()
        role = module.availability_role()
        self.assertIsInstance(role, Group)


class TeacherEventsManageModuleIsCompletedTest(TestCase):
    """Tests for isCompleted method."""

    def setUp(self):
        super().setUp()
        _setup_roles()

    def test_is_completed_false_when_no_events(self):
        """isCompleted should return False when no teacher events exist."""
        module = TeacherEventsManageModule()
        mock_program = MagicMock()
        with patch.object(TeacherEventsManageModule, 'program', mock_program):
            from esp.cal.models import Event
            with patch.object(Event.objects, 'filter') as mock_filter:
                mock_filter.return_value.exists.return_value = False
                result = module.isCompleted()
                self.assertFalse(result)

    def test_is_completed_true_when_events_exist(self):
        """isCompleted should return True when teacher events exist."""
        module = TeacherEventsManageModule()
        mock_program = MagicMock()
        with patch.object(TeacherEventsManageModule, 'program', mock_program):
            from esp.cal.models import Event
            with patch.object(Event.objects, 'filter') as mock_filter:
                mock_filter.return_value.exists.return_value = True
                result = module.isCompleted()
                self.assertTrue(result)


class TeacherEventsManageModuleViewTest(ProgramFrameworkTest):
    """View-level tests for TeacherEventsManageModule using real HTTP requests."""

    def setUp(self):
        modules = [
            ProgramModule.objects.get(handler='TeacherEventsManageModule'),
            ProgramModule.objects.get(handler='AdminCore'),
        ]
        super().setUp(modules=modules)

        self.adminUser, created = ESPUser.objects.get_or_create(
            username='teachereventsadmin'
        )
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()

        self.student = self.students[0]
        self.student.set_password('password')
        self.student.save()

        self.url = '/manage/' + self.program.url + '/teacher_events'

    def test_admin_can_access_teacher_events_view(self):
        """Admin users should get 200 response from teacher_events view."""
        self.client.login(username='teachereventsadmin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_redirected(self):
        """Unauthenticated users should be redirected."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_view_contains_prog_in_context(self):
        """teacher_events view should include prog in context."""
        self.client.login(username='teachereventsadmin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('prog', response.context)

    def test_view_contains_teacher_event_types_in_context(self):
        """teacher_events view should include teacher_event_types in context."""
        self.client.login(username='teachereventsadmin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('teacher_event_types', response.context)

    def test_view_contains_timeslot_form_in_context(self):
        """teacher_events view should include timeslot_form in context."""
        self.client.login(username='teachereventsadmin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('timeslot_form', response.context)

    def test_view_contains_teacher_event_times_in_context(self):
        """teacher_events view should include teacher_event_times in context."""
        self.client.login(username='teachereventsadmin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('teacher_event_times', response.context)

    def test_non_admin_cannot_see_management_content(self):
        """Non-admin users should not see teacher events management content."""
        self.client.login(
            username=self.student.username,
            password='password'
        )
        response = self.client.get(self.url)
        self.assertNotContains(
            response,
            'Teacher Training / Interviews',
            status_code=response.status_code
        )

    def test_post_delete_removes_event(self):
        """POST with command=delete should delete the event."""
        self.client.login(username='teachereventsadmin', password='password')
        event_type, _ = EventType.objects.get_or_create(
            description='Interview',
            defaults={'is_teacher_type': True}
        )
        from esp.cal.models import Event
        import datetime
        event = Event.objects.create(
            program=self.program,
            event_type=event_type,
            start=datetime.datetime(2026, 6, 1, 9, 0),
            end=datetime.datetime(2026, 6, 1, 10, 0),
            short_description='Test Event',
            description='Test Event Description',
        )
        event_id = event.id
        self.client.post(self.url, {
            'command': 'delete',
            'id': event_id,
        })
        self.assertFalse(
            Event.objects.filter(id=event_id).exists()
        )
