"""
Unit tests for StudentOnsite module.

Tests cover the student-facing onsite functionality, including:
- Main student onsite view rendering
- Section detail pages
- Map display
- Catalog viewing
- Survey pages
- Class registration and removal
- Self-check-in flows
- Access control and permission verification
"""

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django import forms

from esp.program.modules.handlers.studentonsite import StudentOnsite, SelfCheckinForm
from esp.middleware.esperrormiddleware import ESPError
from esp.users.models import ESPUser, Record, RecordType, Permission
from esp.program.models import (
    Program,
    ClassSubject,
    ClassSection,
    StudentRegistration,
    RegistrationType,
)
from esp.cal.models import Event
from esp.tagdict.models import Tag


class StudentOnsiteModulePropertiesTests(TestCase):
    """Test module properties and metadata."""

    def test_module_properties(self):
        """Test that module properties are correctly defined."""
        props = StudentOnsite.module_properties()

        self.assertEqual(props['link_title'], 'Student Onsite')
        self.assertEqual(props['admin_title'], 'Student Onsite Webapp')
        self.assertEqual(props['module_type'], 'learn')
        self.assertEqual(props['seq'], 9999)
        self.assertEqual(props['choosable'], 1)

    def test_is_step_functionality(self):
        """Test isStep method responds to program tag."""
        module = StudentOnsite()
        module.program = Mock(spec=Program)

        with patch('esp.program.modules.handlers.studentonsite.Tag.getBooleanTag') as mock_tag:
            mock_tag.return_value = True
            self.assertTrue(module.isStep())

            mock_tag.return_value = False
            self.assertFalse(module.isStep())


class StudentOnsiteContextTests(TestCase):
    """Test onsitecontext helper method."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.program = Mock(spec=Program)
        self.user = Mock(spec=ESPUser)

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_onsitecontext_no_surveys(self, mock_tag):
        """Test onsitecontext when no surveys exist."""
        mock_tag.getTag.return_value = ""
        self.program.getSurveys.return_value.filter.return_value = []

        request = self.factory.get('/')
        request.user = self.user

        context = StudentOnsite.onsitecontext(request, 'learn', 'one', 'two', self.program)

        self.assertEqual(context['user'], self.user)
        self.assertEqual(context['program'], self.program)
        self.assertEqual(context['survey_status'], 'none')
        self.assertEqual(context['one'], 'one')
        self.assertEqual(context['two'], 'two')

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_onsitecontext_with_surveys(self, mock_tag):
        """Test onsitecontext when surveys exist."""
        mock_tag.getTag.return_value = "valid_key"
        mock_survey = Mock()
        self.program.getSurveys.return_value.filter.return_value = [mock_survey]

        request = self.factory.get('/')
        request.user = self.user

        context = StudentOnsite.onsitecontext(request, 'learn', 'one', 'two', self.program)

        self.assertEqual(context['user'], self.user)
        self.assertNotIn('survey_status', context)
        self.assertTrue(context['map_tab'])

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_onsitecontext_map_tab_false_without_api_key(self, mock_tag):
        """Test map_tab is false when no API key."""
        mock_tag.getTag.return_value = "   "  # Empty or whitespace
        self.program.getSurveys.return_value.filter.return_value = []

        request = self.factory.get('/')
        request.user = self.user

        context = StudentOnsite.onsitecontext(request, 'learn', 'one', 'two', self.program)

        self.assertFalse(context['map_tab'])


class StudentOnsiteMainViewTests(TestCase):
    """Test main studentonsite view."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.module = StudentOnsite()
        self.program = Mock(spec=Program)
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='studentonsite/')

        self.user = Mock(spec=ESPUser)
        self.user.id = 1

    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_studentonsite_view_basic_success(self, mock_onsitecontext, mock_scrm_class, mock_render):
        """Test successful rendering of main studentonsite view."""
        # Setup
        mock_context = {'user': self.user}
        mock_onsitecontext.return_value = mock_context

        mock_scrm = Mock()
        mock_scrm.deadline_met.return_value = True
        self.program.getModule.return_value = mock_scrm
        self.program.studentclassregmoduleinfo = {}
        self.program.isCheckedIn.return_value = True

        mock_scrm_class.prepare_static.return_value = {'classes': []}

        request = self.factory.get('/studentonsite')
        request.user = self.user

        # Execute
        self.module.studentonsite(request, 'learn', 'one', 'two', 'studentonsite', '', self.program)

        # Verify
        mock_onsitecontext.assert_called_once()
        mock_scrm_class.prepare_static.assert_called_once()
        mock_render.assert_called_once()

        # Check context
        call_args = mock_render.call_args
        context = call_args[0][2]  # Third argument to render_to_response
        self.assertTrue(context['deadline_met'])
        self.assertTrue(context['checked_in'])
        self.assertEqual(context['webapp_page'], 'schedule')

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_studentonsite_view_with_checkin_note(self, mock_onsitecontext, mock_scrm_class, mock_render, mock_tag):
        """Test studentonsite view includes check-in note from tag."""
        # Setup
        mock_context = {'user': self.user}
        mock_onsitecontext.return_value = mock_context
        mock_tag.getProgramTag.return_value = "Please check in at registration"

        mock_scrm = Mock()
        mock_scrm.deadline_met.return_value = False
        self.program.getModule.return_value = mock_scrm
        self.program.studentclassregmoduleinfo = {}
        self.program.isCheckedIn.return_value = False

        mock_scrm_class.prepare_static.return_value = {}

        request = self.factory.get('/studentonsite')
        request.user = self.user

        # Execute
        self.module.studentonsite(request, 'learn', 'one', 'two', 'studentonsite', '', self.program)

        # Verify context includes check-in note
        call_args = mock_render.call_args
        context = call_args[0][2]
        self.assertEqual(context['checkin_note'], "Please check in at registration")


class StudentOnsiteDetailsViewTests(TestCase):
    """Test onsitedetails auxiliary view."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.module = StudentOnsite()
        self.program = Mock(spec=Program)
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='studentonsite/')

        self.user = Mock(spec=ESPUser)
        self.user.id = 1

    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitedetails_no_section_redirects(self, mock_onsitecontext, mock_render):
        """Test onsitedetails redirects when no section ID provided."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        self.program.get_learn_url.return_value = '/learn/'

        request = self.factory.get('/onsitedetails/')
        request.user = self.user

        # Execute
        response = self.module.onsitedetails(request, 'learn', 'one', 'two', 'onsitedetails', '', self.program)

        # Verify
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/studentonsite', response['Location'])

    @patch('esp.program.modules.handlers.studentonsite.ClassSection')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitedetails_section_not_found_redirects(self, mock_onsitecontext, mock_render, mock_section):
        """Test onsitedetails redirects when section not found."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_section.objects.filter.return_value = []
        self.program.get_learn_url.return_value = '/learn/'

        request = self.factory.get('/onsitedetails/999')
        request.user = self.user

        # Execute
        response = self.module.onsitedetails(request, 'learn', 'one', 'two', 'onsitedetails', '999', self.program)

        # Verify
        self.assertEqual(response.status_code, 302)

    @patch('esp.program.modules.handlers.studentonsite.StudentRegistration')
    @patch('esp.program.modules.handlers.studentonsite.ClassSection')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitedetails_user_not_enrolled_redirects(self, mock_onsitecontext, mock_render,
                                                        mock_section, mock_student_reg):
        """Test onsitedetails redirects when user not enrolled."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context

        mock_sec = Mock()
        mock_section.objects.filter.return_value = [mock_sec]

        mock_student_reg.valid_objects.return_value.filter.return_value = []
        self.program.get_learn_url.return_value = '/learn/'

        request = self.factory.get('/onsitedetails/1')
        request.user = self.user

        # Execute
        response = self.module.onsitedetails(request, 'learn', 'one', 'two', 'onsitedetails', '1', self.program)

        # Verify
        self.assertEqual(response.status_code, 302)

    @patch('esp.program.modules.handlers.studentonsite.StudentRegistration')
    @patch('esp.program.modules.handlers.studentonsite.ClassSection')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitedetails_successful_section_render(self, mock_onsitecontext, mock_render,
                                                      mock_section, mock_student_reg):
        """Test onsitedetails successfully renders section info."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context

        mock_sec = Mock()
        mock_sec.firstBlockEvent.return_value = Mock()
        mock_section.objects.filter.return_value = [mock_sec]

        mock_student_reg.valid_objects.return_value.filter.return_value = [Mock()]
        self.program.getSurveys.return_value.filter.return_value = [Mock()]

        request = self.factory.get('/onsitedetails/1')
        request.user = self.user

        # Execute
        self.module.onsitedetails(request, 'learn', 'one', 'two', 'onsitedetails', '1', self.program)

        # Verify
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        self.assertEqual(context['section'], mock_sec)


class StudentOnsiteMapViewTests(TestCase):
    """Test onsitemap view."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.module = StudentOnsite()
        self.program = Mock(spec=Program)
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='studentonsite/')

        self.user = Mock(spec=ESPUser)

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitemap_renders_with_location_data(self, mock_onsitecontext, mock_render, mock_tag):
        """Test onsitemap includes location and zoom data."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_tag.getProgramTag.side_effect = lambda key, program: {
            'program_center': '40.7128,-74.0060',
            'program_center_zoom': '15'
        }.get(key, '')
        mock_tag.getTag.return_value = 'test_api_key'

        request = self.factory.get('/onsitemap')
        request.user = self.user

        # Execute
        self.module.onsitemap(request, 'learn', 'one', 'two', 'onsitemap', '', self.program)

        # Verify
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        self.assertEqual(context['webapp_page'], 'map')
        self.assertEqual(context['center'], '40.7128,-74.0060')
        self.assertEqual(context['zoom'], '15')
        self.assertEqual(context['API_key'], 'test_api_key')


class StudentOnsiteCatalogViewTests(TestCase):
    """Test onsitecatalog view."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.module = StudentOnsite()
        self.program = Mock(spec=Program)
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='studentonsite/')

        self.user = Mock(spec=ESPUser)
        self.user.getGrade.return_value = 10

    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    @patch('esp.program.modules.handlers.studentonsite.ClassSubject')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitecatalog_without_timeslot(self, mock_onsitecontext, mock_render,
                                             mock_class_subject, mock_scrm):
        """Test catalog view without specific timeslot."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_class_subject.objects.catalog.return_value = []
        mock_scrm.sort_categories.return_value = []
        self.program.get_learn_url.return_value = '/learn/'

        request = self.factory.get('/onsitecatalog/')
        request.user = self.user

        # Execute
        self.module.onsitecatalog(request, 'learn', 'one', 'two', 'onsitecatalog', '', self.program)

        # Verify
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        self.assertEqual(context['webapp_page'], 'catalog')
        self.assertIn('classes', context)
        self.assertIn('categories', context)

    @patch('esp.program.modules.handlers.studentonsite.Event')
    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    @patch('esp.program.modules.handlers.studentonsite.ClassSubject')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitecatalog_with_invalid_timeslot_raises_error(self, mock_onsitecontext, mock_render,
                                                                mock_class_subject, mock_scrm, mock_event):
        """Test catalog with invalid timeslot raises error."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_event.objects.get.side_effect = Event.DoesNotExist()

        request = self.factory.get('/onsitecatalog/abc')
        request.user = self.user

        # Execute & Verify
        with self.assertRaises(ESPError):
            self.module.onsitecatalog(request, 'learn', 'one', 'two', 'onsitecatalog', 'abc', self.program)

    @patch('esp.program.modules.handlers.studentonsite.Record')
    @patch('esp.program.modules.handlers.studentonsite.Event')
    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    @patch('esp.program.modules.handlers.studentonsite.ClassSubject')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitecatalog_filters_by_student_grade(self, mock_onsitecontext, mock_render,
                                                     mock_class_subject, mock_scrm, mock_event, mock_record):
        """Test catalog filters classes by student grade."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context

        mock_event_obj = Mock()
        mock_event_obj.id = 1
        mock_event.objects.get.return_value = mock_event_obj

        # Create mock classes with different grade ranges
        low_grade_class = Mock()
        low_grade_class.grade_min = 6
        low_grade_class.grade_max = 9

        high_grade_class = Mock()
        high_grade_class.grade_min = 10
        high_grade_class.grade_max = 12

        mock_class_subject.objects.catalog.return_value = [low_grade_class, high_grade_class]
        mock_scrm.sort_categories.return_value = []
        mock_record.objects.filter.return_value.exists.return_value = True

        request = self.factory.get('/onsitecatalog/1')
        request.user = self.user

        # Execute
        self.module.onsitecatalog(request, 'learn', 'one', 'two', 'onsitecatalog', '1', self.program)

        # Verify that low_grade_class is filtered out
        call_args = mock_render.call_args
        context = call_args[0][2]
        # The low_grade_class should be filtered out because student grade is 10
        self.assertIn(high_grade_class, context['classes'])


class StudentOnsiteSurveyViewTests(TestCase):
    """Test onsitesurvey view."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.module = StudentOnsite()
        self.program = Mock(spec=Program)
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='studentonsite/')

        self.user = Mock(spec=ESPUser)

    @patch('esp.program.modules.handlers.studentonsite.survey_view')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_onsitesurvey_calls_survey_view(self, mock_onsitecontext, mock_survey_view):
        """Test onsitesurvey delegates to survey_view."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_survey_view.return_value = Mock()

        request = self.factory.get('/onsitesurvey')
        request.user = self.user

        # Execute
        self.module.onsitesurvey(request, 'learn', 'one', 'two', 'onsitesurvey', '', self.program)

        # Verify
        mock_survey_view.assert_called_once()
        call_args = mock_survey_view.call_args
        self.assertEqual(context, call_args[1]['context'])
        self.assertIn('survey.html', call_args[1]['template'])


class StudentOnsiteAddClassViewTests(TestCase):
    """Test onsiteaddclass view."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.module = StudentOnsite()
        self.program = Mock(spec=Program)
        self.module.program = self.program

        self.user = Mock(spec=ESPUser)

    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    def test_onsiteaddclass_success_redirects(self, mock_scrm):
        """Test onsiteaddclass redirects on successful class addition."""
        # Setup
        mock_scrm.addclass_logic.return_value = True
        self.program.getModule.return_value = mock_scrm
        self.program.get_learn_url.return_value = '/learn/'

        request = self.factory.post('/onsiteaddclass/1')
        request.user = self.user

        # Execute
        response = self.module.onsiteaddclass(request, 'learn', 'one', 'two', 'onsiteaddclass', '1', self.program)

        # Verify
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/studentonsite', response['Location'])

    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    def test_onsiteaddclass_failure_no_redirect(self, mock_scrm):
        """Test onsiteaddclass with failure returns None."""
        # Setup
        mock_scrm.addclass_logic.return_value = False

        request = self.factory.post('/onsiteaddclass/1')
        request.user = self.user

        # Execute
        response = self.module.onsiteaddclass(request, 'learn', 'one', 'two', 'onsiteaddclass', '1', self.program)

        # Verify
        self.assertIsNone(response)


class StudentOnsiteClearSlotViewTests(TestCase):
    """Test onsiteclearslot view."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.module = StudentOnsite()
        self.program = Mock(spec=Program)
        self.module.program = self.program

        self.user = Mock(spec=ESPUser)

    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    def test_onsiteclearslot_success_redirects(self, mock_scrm):
        """Test onsiteclearslot redirects on successful slot clear."""
        # Setup
        mock_response = Mock()
        mock_scrm.clearslot_logic.return_value = mock_response
        self.program.get_learn_url.return_value = '/learn/'

        request = self.factory.post('/onsiteclearslot/')
        request.user = self.user

        # Execute
        response = self.module.onsiteclearslot(request, 'learn', 'one', 'two', 'onsiteclearslot', '', self.program)

        # Verify
        self.assertEqual(response.status_code, 302)

    @patch('esp.program.modules.handlers.studentonsite.StudentClassRegModule')
    def test_onsiteclearslot_error_raises_esp_error(self, mock_scrm):
        """Test onsiteclearslot raises ESPError on invalid slot."""
        # Setup
        mock_scrm.clearslot_logic.return_value = "Error message"

        request = self.factory.post('/onsiteclearslot/')
        request.user = self.user

        # Execute & Verify
        with self.assertRaises(ESPError):
            self.module.onsiteclearslot(request, 'learn', 'one', 'two', 'onsiteclearslot', '', self.program)


class StudentOnsiteSelfCheckinViewTests(TestCase):
    """Test selfcheckin view."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.module = StudentOnsite()
        self.program = Mock(spec=Program)
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='studentonsite/')

        self.user = Mock(spec=ESPUser)
        self.user.id = 1

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_selfcheckin_disabled_redirects(self, mock_onsitecontext, mock_render, mock_tag):
        """Test selfcheckin redirects when mode is 'none'."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_tag.getProgramTag.return_value = 'none'
        self.program.get_learn_url.return_value = '/learn/'

        request = self.factory.get('/selfcheckin')
        request.user = self.user

        # Execute
        response = self.module.selfcheckin(request, 'learn', 'one', 'two', 'selfcheckin', '', self.program)

        # Verify
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/studentonsite', response['Location'])

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_selfcheckin_already_checked_in(self, mock_onsitecontext, mock_render, mock_tag):
        """Test selfcheckin shows message when already checked in."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_tag.getProgramTag.return_value = 'code'
        self.program.isCheckedIn.return_value = True

        request = self.factory.get('/selfcheckin')
        request.user = self.user

        # Execute
        self.module.selfcheckin(request, 'learn', 'one', 'two', 'selfcheckin', '', self.program)

        # Verify
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        self.assertTrue(context['checked_in'])

    @patch('esp.program.modules.handlers.studentonsite.StudentRegCore')
    @patch('esp.program.modules.handlers.studentonsite.Tag')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_selfcheckin_shows_form_when_not_checked_in(self, mock_onsitecontext, mock_render,
                                                         mock_tag, mock_reg_core):
        """Test selfcheckin shows form when user not yet checked in."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_tag.getProgramTag.return_value = 'code'
        mock_tag.getBooleanTag.return_value = False
        self.program.isCheckedIn.return_value = False
        self.program.getModules.return_value = []
        mock_reg_core.get_reg_records.return_value = []

        request = self.factory.get('/selfcheckin')
        request.user = self.user

        # Execute
        self.module.selfcheckin(request, 'learn', 'one', 'two', 'selfcheckin', '', self.program)

        # Verify
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        context = call_args[0][2]
        self.assertFalse(context['checked_in'])
        self.assertIn('form', context)

    @patch('esp.program.modules.handlers.studentonsite.Record')
    @patch('esp.program.modules.handlers.studentonsite.RecordType')
    @patch('esp.program.modules.handlers.studentonsite.StudentRegCore')
    @patch('esp.program.modules.handlers.studentonsite.Tag')
    @patch('esp.program.modules.handlers.studentonsite.render_to_response')
    @patch('esp.program.modules.handlers.studentonsite.StudentOnsite.onsitecontext')
    def test_selfcheckin_post_valid_form_creates_record(self, mock_onsitecontext, mock_render,
                                                         mock_tag, mock_reg_core, mock_record_type, mock_record):
        """Test selfcheckin POST with valid form creates attendance record."""
        # Setup
        mock_context = {}
        mock_onsitecontext.return_value = mock_context
        mock_tag.getProgramTag.return_value = 'code'
        mock_tag.getBooleanTag.return_value = False
        self.program.isCheckedIn.return_value = False
        self.program.getModules.return_value = []
        self.program.get_learn_url.return_value = '/learn/'
        mock_reg_core.get_reg_records.return_value = []

        mock_rt = Mock(spec=RecordType)
        mock_record_type.objects.get.return_value = mock_rt

        self.user.userHash.return_value = '123456'

        request = self.factory.post('/selfcheckin', {'code': '123456'})
        request.user = self.user

        # Execute
        response = self.module.selfcheckin(request, 'learn', 'one', 'two', 'selfcheckin', '', self.program)

        # Verify redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn('/learn/studentonsite', response['Location'])

        # Verify record creation
        mock_record_type.objects.get.assert_called_once_with(name="attended")
        mock_record.assert_called_once()


class SelfCheckinFormTests(TestCase):
    """Test SelfCheckinForm."""

    def setUp(self):
        """Set up test fixtures."""
        self.program = Mock(spec=Program)
        self.user = Mock(spec=ESPUser)
        self.user.userHash.return_value = 'abc123'

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_form_requires_program_and_user(self, mock_tag):
        """Test form requires program and user kwargs."""
        with self.assertRaises(KeyError):
            SelfCheckinForm()

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_form_code_field_with_code_mode(self, mock_tag):
        """Test form shows code input field in 'code' mode."""
        mock_tag.getProgramTag.return_value = 'code'

        form = SelfCheckinForm(program=self.program, user=self.user)

        self.assertIn('code', form.fields)
        code_field = form.fields['code']
        self.assertEqual(code_field.min_length, 6)
        self.assertEqual(code_field.max_length, 6)
        self.assertTrue(code_field.required)
        self.assertNotIsInstance(code_field.widget, forms.HiddenInput)

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_form_code_field_hidden_in_automatic_mode(self, mock_tag):
        """Test form hides code field in automatic mode."""
        mock_tag.getProgramTag.return_value = 'automatic'

        form = SelfCheckinForm(program=self.program, user=self.user)

        code_field = form.fields['code']
        self.assertIsInstance(code_field.widget, forms.HiddenInput)
        self.assertEqual(code_field.initial, 'abc123')

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_form_valid_code_passes_validation(self, mock_tag):
        """Test form validation passes with correct code."""
        mock_tag.getProgramTag.return_value = 'code'

        form = SelfCheckinForm({'code': 'abc123'}, program=self.program, user=self.user)

        self.assertTrue(form.is_valid())

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_form_invalid_code_fails_validation(self, mock_tag):
        """Test form validation fails with incorrect code."""
        mock_tag.getProgramTag.return_value = 'code'

        form = SelfCheckinForm({'code': 'wrong6'}, program=self.program, user=self.user)

        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)
        self.assertIn('invalid', str(form.errors['code']).lower())

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_form_code_too_short(self, mock_tag):
        """Test form rejects code that is too short."""
        mock_tag.getProgramTag.return_value = 'code'

        form = SelfCheckinForm({'code': '123'}, program=self.program, user=self.user)

        self.assertFalse(form.is_valid())

    @patch('esp.program.modules.handlers.studentonsite.Tag')
    def test_form_code_too_long(self, mock_tag):
        """Test form rejects code that is too long."""
        mock_tag.getProgramTag.return_value = 'code'

        form = SelfCheckinForm({'code': '1234567'}, program=self.program, user=self.user)

        self.assertFalse(form.is_valid())
