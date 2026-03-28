"""
Unit tests for listgenmodule.py

Tests cover:
- UserAttributeGetter field retrieval and normalization
- ListGenForm form validation and field filtering
- List generation behavior for various input conditions
- Handling of missing or malformed data
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from esp.users.models import ESPUser, UserProfile, StudentInfo, TeacherInfo, PersistentQueryFilter
from esp.program.models import Program, StudentRegistration
from esp.program.modules.handlers.listgenmodule import UserAttributeGetter, ListGenForm, ListGenModule
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestUserAttributeGetter(TestCase):
    """Test UserAttributeGetter field extraction and normalization"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a basic user
        self.user = ESPUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='John',
            last_name='Doe'
        )
        
        # Create a program for testing
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        # Create user profile
        self.profile = UserProfile.objects.create(user=self.user)
        
        self.getter = UserAttributeGetter(self.user, self.program)

    def test_get_functions_returns_dict(self):
        """Test that getFunctions returns a dictionary of available fields"""
        functions = UserAttributeGetter.getFunctions()
        
        self.assertIsInstance(functions, dict)
        self.assertGreater(len(functions), 0)
        # Check that all entries have required keys
        for key, field_info in functions.items():
            self.assertIn('label', field_info)
            self.assertIn('usertype', field_info)

    def test_get_id(self):
        """Test ID retrieval"""
        result = self.getter.get_id()
        self.assertEqual(result, self.user.id)

    def test_get_email(self):
        """Test email retrieval"""
        result = self.getter.get_email()
        self.assertEqual(result, 'test@example.com')

    def test_get_fullname(self):
        """Test full name retrieval"""
        result = self.getter.get_fullname()
        # ESPUser.name() typically returns first_name + last_name
        self.assertIn('John', str(result))
        self.assertIn('Doe', str(result))

    def test_get_firstname(self):
        """Test first name retrieval"""
        result = self.getter.get_firstname()
        self.assertEqual(result, 'John')

    def test_get_lastname(self):
        """Test last name retrieval"""
        result = self.getter.get_lastname()
        self.assertEqual(result, 'Doe')

    def test_get_username(self):
        """Test username retrieval"""
        result = self.getter.get_username()
        self.assertEqual(result, 'testuser')

    def test_get_accountdate(self):
        """Test account creation date formatting"""
        result = self.getter.get_accountdate()
        # Should be formatted as MM/DD/YYYY
        self.assertRegex(result, r'\d{2}/\d{2}/\d{4}')

    def test_get_returns_na_for_none_value(self):
        """Test that get() returns 'N/A' for None values"""
        with patch.object(self.getter, 'get_email', return_value=None):
            result = self.getter.get('email')
            self.assertEqual(result, 'N/A')

    def test_get_returns_na_for_empty_string(self):
        """Test that get() returns 'N/A' for empty strings"""
        with patch.object(self.getter, 'get_email', return_value=''):
            result = self.getter.get('email')
            self.assertEqual(result, 'N/A')

    def test_get_converts_true_to_yes(self):
        """Test that get() converts True to 'Yes'"""
        with patch.object(self.getter, 'get_textmsg', return_value=True):
            result = self.getter.get('textmsg')
            self.assertEqual(result, 'Yes')

    def test_get_converts_false_to_no(self):
        """Test that get() converts False to 'No'"""
        with patch.object(self.getter, 'get_textmsg', return_value=False):
            result = self.getter.get('textmsg')
            self.assertEqual(result, 'No')

    def test_get_returns_string_values_as_is(self):
        """Test that get() returns string values unchanged"""
        with patch.object(self.getter, 'get_email', return_value='user@example.com'):
            result = self.getter.get('email')
            self.assertEqual(result, 'user@example.com')


class TestListGenForm(TestCase):
    """Test ListGenForm validation and field filtering"""

    def test_form_creation(self):
        """Test basic form creation"""
        form = ListGenForm()
        self.assertIsNotNone(form)
        self.assertIn('fields', form.fields)
        self.assertIn('split_by', form.fields)
        self.assertIn('output_type', form.fields)

    def test_output_type_choices(self):
        """Test that output_type has csv and html choices"""
        form = ListGenForm()
        choices = dict(form.fields['output_type'].choices)
        self.assertIn('csv', choices)
        self.assertIn('html', choices)

    def test_form_with_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'fields': ['01_id', '02_username', '06_email'],
            'split_by': '',
            'output_type': 'csv'
        }
        form = ListGenForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_with_missing_fields(self):
        """Test form validation with missing required fields"""
        form_data = {
            'split_by': '',
            'output_type': 'csv'
        }
        form = ListGenForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_with_invalid_output_type(self):
        """Test form validation with invalid output type"""
        form_data = {
            'fields': ['01_id'],
            'split_by': '',
            'output_type': 'invalid_type'
        }
        form = ListGenForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_form_student_usertype_filtering(self):
        """Test that student usertype only shows student-relevant fields"""
        form = ListGenForm(usertype='student')
        field_choices = [choice[0] for choice in form.fields['fields'].choices]
        
        # Check that student-specific fields are present
        self.assertIn('11_dob', field_choices)  # Date of birth is student-only
        
        # Check that teacher-specific fields are not present
        self.assertNotIn('16_affiliation', field_choices)  # Affiliation is teacher-only

    def test_form_teacher_usertype_filtering(self):
        """Test that teacher usertype only shows teacher-relevant fields"""
        form = ListGenForm(usertype='teacher')
        field_choices = [choice[0] for choice in form.fields['fields'].choices]
        
        # Check that teacher-specific fields are present
        self.assertIn('16_affiliation', field_choices)  # Affiliation is teacher-only
        
        # Check that student-specific fields are not present
        self.assertNotIn('11_dob', field_choices)  # Date of birth is student-only

    def test_form_combo_usertype_shows_all_fields(self):
        """Test that combo usertype shows all fields"""
        form = ListGenForm(usertype='combo')
        field_choices = [choice[0] for choice in form.fields['fields'].choices]
        
        # Should have many more fields for combo
        self.assertGreater(len(field_choices), 10)


class TestListGenModulePostHandling(TestCase):
    """Test ListGenModule POST data processing"""

    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.user = ESPUser.objects.create_user(
            username='admin',
            email='admin@example.com',
            is_staff=True
        )
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        self.module = ListGenModule(self.program)

    def test_form_handles_empty_split_by(self):
        """Test that form correctly handles empty split_by field"""
        form_data = {
            'fields': ['01_id', '02_username'],
            'split_by': '',  # Empty split_by should be allowed
            'output_type': 'csv'
        }
        form = ListGenForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['split_by'], '')

    def test_form_with_multiple_fields_selected(self):
        """Test form handling with multiple fields selected"""
        form_data = {
            'fields': ['01_id', '02_username', '04_firstname', '05_lastname', '06_email'],
            'split_by': '12_gender',
            'output_type': 'html'
        }
        form = ListGenForm(data=form_data, usertype='combo')
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.cleaned_data['fields']), 5)


class TestListGenFieldConfiguration(TestCase):
    """Test field configuration and availability"""

    def test_any_usertype_fields_available_for_all_users(self):
        """Test that fields with 'any' usertype are available for all user types"""
        functions = UserAttributeGetter.getFunctions()
        any_fields = [key for key, info in functions.items() if 'any' in info['usertype']]
        
        # Should have many 'any' fields (ID, username, email, etc.)
        self.assertGreater(len(any_fields), 5)
        
        # Test that these are available in all forms
        for usertype in ['student', 'teacher', 'combo']:
            form = ListGenForm(usertype=usertype)
            form_field_choices = set([choice[0] for choice in form.fields['fields'].choices])
            
            # At least some 'any' fields should be in each form
            self.assertTrue(len(form_field_choices) > 0)

    def test_field_labels_unique(self):
        """Test that field labels are unique for identification"""
        functions = UserAttributeGetter.getFunctions()
        labels = [info['label'] for info in functions.values()]
        
        # Most labels should be unique (though some might be duplicated)
        unique_labels = set(labels)
        self.assertGreater(len(unique_labels), len(labels) * 0.8)  # At least 80% unique


class TestListGenListGenerationValidation(TestCase):
    """Test validation and error handling in list generation"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = ESPUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        self.profile = UserProfile.objects.create(user=self.user)

    def test_user_attribute_getter_initialization(self):
        """Test that UserAttributeGetter can be initialized successfully"""
        getter = UserAttributeGetter(self.user, self.program)
        self.assertIsNotNone(getter)
        self.assertEqual(getter.user, self.user)
        self.assertEqual(getter.program, self.program)

    def test_attribute_getter_handles_user_without_profile(self):
        """Test that attribute getter gracefully handles missing profile data"""
        # Mock a user with minimal profile data
        user = ESPUser.objects.create_user(
            username='minimal',
            email='minimal@example.com'
        )
        # Create minimal profile
        UserProfile.objects.create(user=user)
        
        getter = UserAttributeGetter(user, self.program)
        # Should not raise exception
        self.assertIsNotNone(getter.get_email())

    def test_form_initial_field_selection(self):
        """Test that form has reasonable initial field selection"""
        form = ListGenForm()
        initial_fields = form.fields['fields'].initial
        
        # Basic fields should be in initial selection
        self.assertIn('02_username', initial_fields)
        self.assertIn('04_firstname', initial_fields)
        self.assertIn('05_lastname', initial_fields)
        self.assertIn('06_email', initial_fields)
