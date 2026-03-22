"""
Unit tests for AdminReviewApps module.

Tests cover the admin review functionality for accepting/rejecting students
and viewing their applications.
"""

from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser

from esp.program.modules.handlers.adminreviewapps import AdminReviewApps
from esp.middleware.esperrormiddleware import ESPError
from esp.users.models import ESPUser
from esp.program.models import (
    Program,
    ClassSubject,
    StudentRegistration,
    RegistrationType,
    StudentApplication,
)


class AdminReviewAppsModulePropertiesTests(TestCase):
    """Test module properties and metadata."""

    def test_module_properties(self):
        """Test that module properties are correctly defined."""
        props = AdminReviewApps.module_properties()

        self.assertEqual(props['admin_title'], 'Application Review for Admin')
        self.assertEqual(props['link_title'], 'Application Review for Admin')
        self.assertEqual(props['module_type'], 'manage')
        self.assertEqual(props['seq'], 1000)
        self.assertEqual(props['choosable'], 0)

    def test_is_step_false(self):
        """Test that module is not a step."""
        module = AdminReviewApps()
        self.assertFalse(module.isStep())


class AdminReviewAppsStudentsTests(TestCase):
    """Test student filtering methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.program = Mock(spec=Program)
        self.module = AdminReviewApps()
        self.module.program = self.program

    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    def test_students_returns_qobject_format(self, mock_user_class):
        """Test students method returns Q object when requested."""
        result = self.module.students(QObject=True)

        self.assertIn('app_accepted_to_one_program', result)
        self.assertIsNotNone(result['app_accepted_to_one_program'])

    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    def test_students_returns_user_queryset_format(self, mock_user_class):
        """Test students method returns user queryset by default."""
        mock_queryset = Mock()
        mock_user_class.objects.filter().distinct.return_value = mock_queryset

        result = self.module.students(QObject=False)

        self.assertIn('app_accepted_to_one_program', result)
        self.assertEqual(result['app_accepted_to_one_program'], mock_queryset)

    def test_student_desc_returns_description(self):
        """Test that studentDesc returns appropriate descriptions."""
        desc = self.module.studentDesc()

        self.assertIn('app_accepted_to_one_program', desc)
        self.assertEqual(
            desc['app_accepted_to_one_program'],
            "Students who are accepted to at least one class"
        )


class AdminReviewAppsReviewStudentsTests(TestCase):
    """Test review_students view functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.program = Mock(spec=Program)
        self.module = AdminReviewApps()
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='templates/')
        
        self.admin_user = Mock(spec=ESPUser)
        self.admin_user.canEdit = Mock(return_value=True)

    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_review_students_class_not_found(self, mock_class_subject):
        """Test review_students raises error when class not found."""
        mock_class_subject.objects.get.side_effect = ClassSubject.DoesNotExist()
        
        request = self.factory.get('/review/')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.review_students(request, '', '', '', '', 'invalid_id', self.program)
        
        self.assertIn('Cannot find class', str(context.exception))

    @patch('esp.program.modules.handlers.adminreviewapps.render_to_response')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_review_students_user_cannot_edit(self, mock_class_subject, mock_render):
        """Test review_students raises error when user cannot edit class."""
        mock_cls = Mock(spec=ClassSubject)
        mock_class_subject.objects.get.return_value = mock_cls
        
        self.admin_user.canEdit.return_value = False
        
        request = self.factory.get('/review/')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.review_students(request, '', '', '', '', '1', self.program)
        
        self.assertIn('cannot edit class', str(context.exception).lower())

    @patch('esp.program.modules.handlers.adminreviewapps.render_to_response')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_review_students_successful_render(self, mock_class_subject, mock_render):
        """Test review_students successfully renders template."""
        mock_cls = Mock(spec=ClassSubject)
        mock_cls.students_dict.return_value = {}
        mock_class_subject.objects.get.return_value = mock_cls
        mock_render.return_value = Mock()
        
        request = self.factory.get('/review/')
        request.user = self.admin_user
        
        result = self.module.review_students(request, '', '', '', '', '1', self.program)
        
        self.assertIsNotNone(result)
        mock_render.assert_called_once()

    @patch('esp.program.modules.handlers.adminreviewapps.render_to_response')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_review_students_filters_students_with_applications(self, mock_class_subject, mock_render):
        """Test review_students filters only students with applications."""
        # Create mock students
        student1 = Mock(spec=ESPUser)
        student1.studentapplication_set.filter.return_value.count.return_value = 1
        student1.studentregistration_set.filter.return_value = [Mock(start_date=datetime.now())]
        
        student2 = Mock(spec=ESPUser)
        student2.studentapplication_set.filter.return_value.count.return_value = 0
        
        mock_cls = Mock(spec=ClassSubject)
        mock_cls.students_dict.return_value = {'students': [student1, student2]}
        mock_class_subject.objects.get.return_value = mock_cls
        mock_render.return_value = Mock()
        
        request = self.factory.get('/review/')
        request.user = self.admin_user
        
        # Mock StudentRegistration
        with patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration') as mock_reg:
            mock_reg.valid_objects.return_value.filter.return_value.count.return_value = 0
            
            self.module.review_students(request, '', '', '', '', '1', self.program)
            
            # Verify template was called
            mock_render.assert_called_once()

    @patch('esp.program.modules.handlers.adminreviewapps.render_to_response')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_review_students_sorts_by_last_name(self, mock_class_subject, mock_render):
        """Test that students are sorted by last name."""
        student1 = Mock(spec=ESPUser)
        student1.last_name = 'Zebra'
        student1.studentapplication_set.filter.return_value.count.return_value = 1
        student1.studentregistration_set.filter.return_value = [Mock(start_date=datetime.now())]
        
        student2 = Mock(spec=ESPUser)
        student2.last_name = 'Apple'
        student2.studentapplication_set.filter.return_value.count.return_value = 1
        student2.studentregistration_set.filter.return_value = [Mock(start_date=datetime.now())]
        
        mock_cls = Mock(spec=ClassSubject)
        mock_cls.students_dict.return_value = {'students': [student1, student2]}
        mock_class_subject.objects.get.return_value = mock_cls
        mock_render.return_value = Mock()
        
        request = self.factory.get('/review/')
        request.user = self.admin_user
        
        with patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration') as mock_reg:
            mock_reg.valid_objects.return_value.filter.return_value.count.return_value = 0
            
            self.module.review_students(request, '', '', '', '', '1', self.program)
            
            # Get the called arguments
            call_args = mock_render.call_args
            context = call_args[0][2]  # Third argument to render_to_response
            students = context['students']
            
            # Verify sorting
            self.assertEqual(students[0].last_name, 'Apple')
            self.assertEqual(students[1].last_name, 'Zebra')


class AdminReviewAppsAcceptStudentTests(TestCase):
    """Test accept_student functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.program = Mock(spec=Program)
        self.module = AdminReviewApps()
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='templates/')
        self.module.review_students = Mock(return_value=Mock())
        
        self.admin_user = Mock(spec=ESPUser)
        self.admin_user.canEdit = Mock(return_value=True)

    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_accept_student_class_not_found(self, mock_class_subject):
        """Test accept_student raises error when class not found."""
        mock_class_subject.objects.get.side_effect = ClassSubject.DoesNotExist()
        
        request = self.factory.get('/accept/?cls=invalid&student=1')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.accept_student(request, '', '', '', '', '1', self.program)
        
        self.assertIn('Student or class not found', str(context.exception))

    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_accept_student_student_not_found(self, mock_class_subject, mock_user):
        """Test accept_student raises error when student not found."""
        mock_cls = Mock(spec=ClassSubject)
        mock_class_subject.objects.get.return_value = mock_cls
        mock_user.objects.get.side_effect = ESPUser.DoesNotExist()
        
        request = self.factory.get('/accept/?cls=1&student=invalid')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.accept_student(request, '', '', '', '', '1', self.program)
        
        self.assertIn('Student or class not found', str(context.exception))

    @patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration')
    @patch('esp.program.modules.handlers.adminreviewapps.RegistrationType')
    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_accept_student_creates_registration(self, mock_class_subject, mock_user, 
                                                 mock_rtype, mock_sreg):
        """Test accept_student creates student registration."""
        mock_cls = Mock(spec=ClassSubject)
        mock_sec = Mock()
        mock_cls.get_sections.return_value = [mock_sec]
        mock_class_subject.objects.get.return_value = mock_cls
        
        mock_student = Mock(spec=ESPUser)
        mock_user.objects.get.return_value = mock_student
        
        mock_rtype_obj = Mock()
        mock_rtype.objects.get_or_create.return_value = (mock_rtype_obj, True)
        
        request = self.factory.get('/accept/?cls=1&student=1')
        request.user = self.admin_user
        
        self.module.accept_student(request, '', '', '', '', '1', self.program)
        
        # Verify registration was created
        mock_sreg.objects.get_or_create.assert_called_once_with(
            user=mock_student,
            section=mock_sec,
            relationship=mock_rtype_obj
        )
        self.module.review_students.assert_called_once()

    @patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration')
    @patch('esp.program.modules.handlers.adminreviewapps.RegistrationType')
    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_accept_student_calls_review_students(self, mock_class_subject, mock_user,
                                                  mock_rtype, mock_sreg):
        """Test accept_student calls review_students after accepting."""
        mock_cls = Mock(spec=ClassSubject)
        mock_sec = Mock()
        mock_cls.get_sections.return_value = [mock_sec]
        mock_class_subject.objects.get.return_value = mock_cls
        
        mock_student = Mock(spec=ESPUser)
        mock_user.objects.get.return_value = mock_student
        
        mock_rtype_obj = Mock()
        mock_rtype.objects.get_or_create.return_value = (mock_rtype_obj, True)
        
        request = self.factory.get('/accept/?cls=1&student=1')
        request.user = self.admin_user
        
        self.module.accept_student(request, '', '', '', '', '1', self.program)
        
        # Verify review_students was called
        self.module.review_students.assert_called_once_with(
            request, '', '', '', '', '1', self.program
        )


class AdminReviewAppsRejectStudentTests(TestCase):
    """Test reject_student functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.program = Mock(spec=Program)
        self.module = AdminReviewApps()
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='templates/')
        self.module.review_students = Mock(return_value=Mock())
        
        self.admin_user = Mock(spec=ESPUser)
        self.admin_user.canEdit = Mock(return_value=True)

    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_reject_student_class_not_found(self, mock_class_subject):
        """Test reject_student raises error when class not found."""
        mock_class_subject.objects.get.side_effect = ClassSubject.DoesNotExist()
        
        request = self.factory.get('/reject/?cls=invalid&student=1')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.reject_student(request, '', '', '', '', '1', self.program)
        
        self.assertIn('Student or class not found', str(context.exception))

    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_reject_student_student_not_found(self, mock_class_subject, mock_user):
        """Test reject_student raises error when student not found."""
        mock_cls = Mock(spec=ClassSubject)
        mock_class_subject.objects.get.return_value = mock_cls
        mock_user.objects.get.side_effect = ESPUser.DoesNotExist()
        
        request = self.factory.get('/reject/?cls=1&student=invalid')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.reject_student(request, '', '', '', '', '1', self.program)
        
        self.assertIn('Student or class not found', str(context.exception))

    @patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration')
    @patch('esp.program.modules.handlers.adminreviewapps.RegistrationType')
    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_reject_student_expires_registration(self, mock_class_subject, mock_user,
                                                 mock_rtype, mock_sreg):
        """Test reject_student expires student registration."""
        mock_cls = Mock(spec=ClassSubject)
        mock_sec = Mock()
        mock_cls.get_sections.return_value = [mock_sec]
        mock_class_subject.objects.get.return_value = mock_cls
        
        mock_student = Mock(spec=ESPUser)
        mock_user.objects.get.return_value = mock_student
        
        mock_rtype_obj = Mock()
        mock_rtype.objects.get_or_create.return_value = (mock_rtype_obj, True)
        
        mock_reg_obj = Mock()
        mock_sreg.objects.filter.return_value = [mock_reg_obj]
        
        request = self.factory.get('/reject/?cls=1&student=1')
        request.user = self.admin_user
        
        self.module.reject_student(request, '', '', '', '', '1', self.program)
        
        # Verify registration was expired
        mock_reg_obj.expire.assert_called_once()
        self.module.review_students.assert_called_once()

    @patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration')
    @patch('esp.program.modules.handlers.adminreviewapps.RegistrationType')
    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_reject_student_calls_review_students(self, mock_class_subject, mock_user,
                                                  mock_rtype, mock_sreg):
        """Test reject_student calls review_students after rejecting."""
        mock_cls = Mock(spec=ClassSubject)
        mock_sec = Mock()
        mock_cls.get_sections.return_value = [mock_sec]
        mock_class_subject.objects.get.return_value = mock_cls
        
        mock_student = Mock(spec=ESPUser)
        mock_user.objects.get.return_value = mock_student
        
        mock_rtype_obj = Mock()
        mock_rtype.objects.get_or_create.return_value = (mock_rtype_obj, True)
        
        mock_sreg.objects.filter.return_value = []
        
        request = self.factory.get('/reject/?cls=1&student=1')
        request.user = self.admin_user
        
        self.module.reject_student(request, '', '', '', '', '1', self.program)
        
        # Verify review_students was called
        self.module.review_students.assert_called_once_with(
            request, '', '', '', '', '1', self.program
        )


class AdminReviewAppsViewAppTests(TestCase):
    """Test view_app functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.program = Mock(spec=Program)
        self.module = AdminReviewApps()
        self.module.program = self.program
        self.module.baseDir = Mock(return_value='templates/')
        
        self.admin_user = Mock(spec=ESPUser)
        self.admin_user.canEdit = Mock(return_value=True)

    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_view_app_class_not_found(self, mock_class_subject):
        """Test view_app raises error when class not found."""
        mock_class_subject.objects.get.side_effect = ClassSubject.DoesNotExist()
        
        request = self.factory.get('/view/?student=1')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.view_app(request, '', '', '', '', 'invalid_id', self.program)
        
        self.assertIn('Cannot find class', str(context.exception))

    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_view_app_student_not_found(self, mock_class_subject, mock_user):
        """Test view_app raises error when student not found."""
        mock_cls = Mock(spec=ClassSubject)
        mock_cls.default_section.return_value = Mock()
        mock_class_subject.objects.get.return_value = mock_cls
        mock_user.objects.get.side_effect = ESPUser.DoesNotExist()
        
        request = self.factory.get('/view/?student=invalid')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.view_app(request, '', '', '', '', '1', self.program)
        
        self.assertIn('Cannot find student', str(context.exception))

    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_view_app_student_not_in_class(self, mock_class_subject, mock_user):
        """Test view_app raises error when student not in class."""
        mock_cls = Mock(spec=ClassSubject)
        mock_cls.default_section.return_value = Mock()
        mock_class_subject.objects.get.return_value = mock_cls
        
        mock_student = Mock(spec=ESPUser)
        mock_student.studentregistration_set.filter.return_value.count.return_value = 0
        mock_user.objects.get.return_value = mock_student
        
        request = self.factory.get('/view/?student=1')
        request.user = self.admin_user
        
        with self.assertRaises(ESPError) as context:
            self.module.view_app(request, '', '', '', '', '1', self.program)
        
        self.assertIn('Student not a student of this class', str(context.exception))

    @patch('esp.program.modules.handlers.adminreviewapps.render_to_response')
    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_view_app_successful(self, mock_class_subject, mock_user, mock_render):
        """Test view_app successfully renders application."""
        mock_cls = Mock(spec=ClassSubject)
        mock_sec = Mock()
        mock_cls.default_section.return_value = mock_sec
        mock_class_subject.objects.get.return_value = mock_cls
        
        mock_student = Mock(spec=ESPUser)
        mock_app = Mock()
        mock_student.studentapplication_set.get.return_value = mock_app
        mock_student.studentregistration_set.filter.return_value.count.return_value = 1
        mock_user.objects.get.return_value = mock_student
        
        mock_scrmi = Mock()
        mock_scrmi.reg_verbs.return_value = {}
        self.program.studentclassregmoduleinfo = mock_scrmi
        
        mock_render.return_value = Mock()
        
        request = self.factory.get('/view/?student=1')
        request.user = self.admin_user
        
        result = self.module.view_app(request, '', '', '', '', '1', self.program)
        
        self.assertIsNotNone(result)
        mock_render.assert_called_once()

    @patch('esp.program.modules.handlers.adminreviewapps.render_to_response')
    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_view_app_student_no_application(self, mock_class_subject, mock_user, mock_render):
        """Test view_app when student has no application."""
        mock_cls = Mock(spec=ClassSubject)
        mock_sec = Mock()
        mock_cls.default_section.return_value = mock_sec
        mock_class_subject.objects.get.return_value = mock_cls
        
        mock_student = Mock(spec=ESPUser)
        mock_student.studentapplication_set.get.side_effect = StudentApplication.DoesNotExist()
        mock_student.studentregistration_set.filter.return_value.count.return_value = 1
        mock_user.objects.get.return_value = mock_student
        
        mock_scrmi = Mock()
        mock_scrmi.reg_verbs.return_value = {}
        self.program.studentclassregmoduleinfo = mock_scrmi
        
        request = self.factory.get('/view/?student=1')
        request.user = self.admin_user
        
        with self.assertRaises(AssertionError):
            self.module.view_app(request, '', '', '', '', '1', self.program)

    @patch('esp.program.modules.handlers.adminreviewapps.render_to_response')
    @patch('esp.program.modules.handlers.adminreviewapps.ESPUser')
    @patch('esp.program.modules.handlers.adminreviewapps.ClassSubject')
    def test_view_app_with_post_student_id(self, mock_class_subject, mock_user, mock_render):
        """Test view_app retrieves student from POST data."""
        mock_cls = Mock(spec=ClassSubject)
        mock_sec = Mock()
        mock_cls.default_section.return_value = mock_sec
        mock_class_subject.objects.get.return_value = mock_cls
        
        mock_student = Mock(spec=ESPUser)
        mock_app = Mock()
        mock_student.studentapplication_set.get.return_value = mock_app
        mock_student.studentregistration_set.filter.return_value.count.return_value = 1
        mock_user.objects.get.return_value = mock_student
        
        mock_scrmi = Mock()
        mock_scrmi.reg_verbs.return_value = {}
        self.program.studentclassregmoduleinfo = mock_scrmi
        
        mock_render.return_value = Mock()
        
        request = self.factory.post('/view/', {'student': '1'})
        request.user = self.admin_user
        
        result = self.module.view_app(request, '', '', '', '', '1', self.program)
        
        self.assertIsNotNone(result)
        mock_render.assert_called_once()


class AdminReviewAppsPrepareTests(TestCase):
    """Test prepare method."""

    def setUp(self):
        """Set up test fixtures."""
        self.program = Mock(spec=Program)
        self.module = AdminReviewApps()
        self.module.program = self.program

    def test_prepare_sets_classes_to_review(self):
        """Test prepare sets classes_to_review in context."""
        mock_classes = [Mock(), Mock()]
        self.program.classes.return_value = mock_classes
        
        context = {}
        result = self.module.prepare(context)
        
        self.assertIn('classes_to_review', result)
        self.assertEqual(result['classes_to_review'], mock_classes)

    def test_prepare_returns_context(self):
        """Test prepare returns the modified context."""
        self.program.classes.return_value = []
        
        context = {'existing_key': 'value'}
        result = self.module.prepare(context)
        
        self.assertIn('existing_key', result)
        self.assertEqual(result['existing_key'], 'value')


class AdminReviewAppsGetMsgVarsTests(TestCase):
    """Test get_msg_vars method."""

    def setUp(self):
        """Set up test fixtures."""
        self.program = Mock(spec=Program)
        self.module = AdminReviewApps()
        self.module.program = self.program

    @patch.object(AdminReviewApps, 'getSchedule')
    def test_get_msg_vars_schedule_app(self, mock_get_schedule):
        """Test get_msg_vars returns schedule for schedule_app key."""
        mock_student = Mock(spec=ESPUser)
        mock_schedule = 'Student schedule...'
        mock_get_schedule.return_value = mock_schedule
        
        result = self.module.get_msg_vars(mock_student, 'schedule_app')
        
        self.assertEqual(result, mock_schedule)
        mock_get_schedule.assert_called_once_with(self.program, mock_student)

    def test_get_msg_vars_unknown_key_returns_none(self):
        """Test get_msg_vars returns None for unknown keys."""
        mock_student = Mock(spec=ESPUser)
        
        result = self.module.get_msg_vars(mock_student, 'unknown_key')
        
        self.assertIsNone(result)


class AdminReviewAppsGetScheduleTests(TestCase):
    """Test getSchedule static method."""

    def test_get_schedule_empty_registrations(self):
        """Test getSchedule with no student registrations."""
        program = Mock(spec=Program)
        student = Mock(spec=ESPUser)
        student.name.return_value = 'John Doe'
        
        with patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration') as mock_sreg:
            mock_sreg.valid_objects.return_value.filter.return_value = []
            
            schedule = AdminReviewApps.getSchedule(program, student)
            
            self.assertIn('John Doe', schedule)
            self.assertIn('Time', schedule)
            self.assertIn('Class', schedule)
            self.assertIn('Room', schedule)

    def test_get_schedule_with_registrations(self):
        """Test getSchedule with student registrations."""
        program = Mock(spec=Program)
        student = Mock(spec=ESPUser)
        student.name.return_value = 'Jane Smith'
        
        mock_class1 = Mock(spec=ClassSubject)
        mock_class1.title = 'Math 101'
        mock_class1.friendly_times.return_value = ['10:00 - 11:00']
        mock_class1.prettyrooms.return_value = ['Room 101']
        
        mock_section1 = Mock()
        mock_section1.parent_class = mock_class1
        
        mock_reg1 = Mock()
        mock_reg1.section = mock_section1
        
        with patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration') as mock_sreg:
            mock_sreg.valid_objects.return_value.filter.return_value = [mock_reg1]
            
            schedule = AdminReviewApps.getSchedule(program, student)
            
            self.assertIn('Jane Smith', schedule)
            self.assertIn('Math 101', schedule)
            self.assertIn('10:00 - 11:00', schedule)
            self.assertIn('Room 101', schedule)

    def test_get_schedule_multiple_registrations_sorted(self):
        """Test getSchedule sorts classes by friendly times."""
        program = Mock(spec=Program)
        student = Mock(spec=ESPUser)
        student.name.return_value = 'Test Student'
        
        mock_class1 = Mock(spec=ClassSubject)
        mock_class1.title = 'Class B'
        mock_class1.friendly_times.return_value = ['14:00 - 15:00']
        mock_class1.prettyrooms.return_value = ['Room B']
        
        mock_class2 = Mock(spec=ClassSubject)
        mock_class2.title = 'Class A'
        mock_class2.friendly_times.return_value = ['10:00 - 11:00']
        mock_class2.prettyrooms.return_value = ['Room A']
        
        mock_section1 = Mock()
        mock_section1.parent_class = mock_class1
        mock_section2 = Mock()
        mock_section2.parent_class = mock_class2
        
        mock_reg1 = Mock()
        mock_reg1.section = mock_section1
        mock_reg2 = Mock()
        mock_reg2.section = mock_section2
        
        with patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration') as mock_sreg:
            mock_sreg.valid_objects.return_value.filter.return_value = [mock_reg1, mock_reg2]
            
            schedule = AdminReviewApps.getSchedule(program, student)
            
            self.assertIn('Test Student', schedule)
            self.assertIn('Class A', schedule)
            self.assertIn('Class B', schedule)

    def test_get_schedule_class_with_no_rooms(self):
        """Test getSchedule displays N/A for classes with no rooms."""
        program = Mock(spec=Program)
        student = Mock(spec=ESPUser)
        student.name.return_value = 'Room Test'
        
        mock_class = Mock(spec=ClassSubject)
        mock_class.title = 'No Room Class'
        mock_class.friendly_times.return_value = ['09:00 - 10:00']
        mock_class.prettyrooms.return_value = []
        
        mock_section = Mock()
        mock_section.parent_class = mock_class
        
        mock_reg = Mock()
        mock_reg.section = mock_section
        
        with patch('esp.program.modules.handlers.adminreviewapps.StudentRegistration') as mock_sreg:
            mock_sreg.valid_objects.return_value.filter.return_value = [mock_reg]
            
            schedule = AdminReviewApps.getSchedule(program, student)
            
            self.assertIn('N/A', schedule)


class AdminReviewAppsIntegrationTests(TestCase):
    """Integration tests for AdminReviewApps module."""

    def test_module_properties_consistency(self):
        """Test that module properties are consistent."""
        props = AdminReviewApps.module_properties()
        
        # Module should be manage type
        self.assertEqual(props['module_type'], 'manage')
        
        # Module should not be choosable by default
        self.assertFalse(props['choosable'])
        
        # Module should have proper titles
        self.assertTrue(len(props['admin_title']) > 0)
        self.assertTrue(len(props['link_title']) > 0)

    def test_meta_class_configuration(self):
        """Test Meta class is properly configured."""
        module = AdminReviewApps()
        
        # Verify proxy model setup
        self.assertTrue(AdminReviewApps._meta.proxy)
        self.assertEqual(AdminReviewApps._meta.app_label, 'modules')
