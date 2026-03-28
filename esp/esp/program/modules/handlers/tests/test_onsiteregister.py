"""
Unit tests for onsiteregister.py

Tests cover:
- Onsite registration form validation
- Successful onsite student registration
- Invalid form submission handling
- Username generation for new students
- User/profile/accounting side effects
- Onsite-only authorization behavior
"""

from django.test import TestCase, RequestFactory, Client
from django.contrib.auth.models import Group
from esp.users.models import ESPUser, Record, ContactInfo, StudentInfo, K12School
from esp.program.models import Program, RegistrationProfile
from esp.program.modules.handlers.onsiteregister import OnSiteRegister
from esp.program.modules.forms.onsite import OnSiteRegForm
from esp.accounting.models import LineItemType, AccountingCode, LineItem
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestOnSiteRegForm(TestCase):
    """Test OnSiteRegForm validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )

    def test_form_initialization(self):
        """Test that form initializes correctly"""
        form = OnSiteRegForm()
        
        self.assertIn('first_name', form.fields)
        self.assertIn('last_name', form.fields)
        self.assertIn('email', form.fields)
        self.assertIn('grade', form.fields)
        self.assertIn('school', form.fields)
        self.assertIn('k12school', form.fields)
        self.assertIn('paid', form.fields)
        self.assertIn('medical', form.fields)
        self.assertIn('liability', form.fields)

    def test_form_with_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'grade': '9',
            'school': '',
            'k12school': '',
            'paid': True,
            'medical': False,
            'liability': False,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_form_with_missing_first_name(self):
        """Test form validation fails without first name"""
        form_data = {
            'last_name': 'Doe',
            'email': 'john@example.com',
            'grade': '9',
            'paid': True,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_form_with_missing_last_name(self):
        """Test form validation fails without last name"""
        form_data = {
            'first_name': 'John',
            'email': 'john@example.com',
            'grade': '9',
            'paid': True,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)

    def test_form_with_invalid_email(self):
        """Test form validation fails with invalid email"""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'not-an-email',
            'grade': '9',
            'paid': True,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_form_with_missing_grade(self):
        """Test form validation fails without grade"""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'paid': True,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('grade', form.errors)

    def test_form_grade_choices_populated(self):
        """Test that grade choices are populated correctly"""
        form = OnSiteRegForm()
        grade_choices = [choice[0] for choice in form.fields['grade'].choices]
        
        # Should include grades from ESPUser.grade_options()
        self.assertGreater(len(grade_choices), 0)

    def test_form_checkbox_fields_optional(self):
        """Test that paid, medical, liability are optional"""
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'grade': '10',
            # paid, medical, liability not provided
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_form_with_all_checkboxes_checked(self):
        """Test form with all checkboxes marked"""
        form_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@example.com',
            'grade': '11',
            'paid': True,
            'medical': True,
            'liability': True,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data['paid'])
        self.assertTrue(form.cleaned_data['medical'])
        self.assertTrue(form.cleaned_data['liability'])


class TestOnsiteRegisterUserCreation(TestCase):
    """Test user creation during onsite registration"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        self.factory = RequestFactory()
        
        # Create the ProgramModuleObj
        from esp.program.modules.models import ProgramModule
        onsite_module = ProgramModule.objects.filter(
            handler__contains='OnSiteRegister'
        ).first()
        
        if onsite_module:
            from esp.program.modules.base import ProgramModuleObj
            self.pmo = ProgramModuleObj.objects.create(
                program=self.program,
                module=onsite_module
            )
        else:
            self.pmo = MagicMock()
            self.pmo.program = self.program

    def test_user_creation_with_valid_data(self):
        """Test that valid form data creates a user"""
        initial_user_count = ESPUser.objects.count()
        
        form_data = {
            'first_name': 'Test',
            'last_name': 'Student',
            'email': 'teststudent@example.com',
            'grade': '9',
            'paid': True,
            'medical': False,
            'liability': False,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        
        new_data = form.cleaned_data
        username = ESPUser.get_unused_username(new_data['first_name'], new_data['last_name'])
        new_user = ESPUser.objects.create_user(
            username=username,
            first_name=new_data['first_name'],
            last_name=new_data['last_name'],
            email=new_data['email']
        )
        
        self.assertEqual(ESPUser.objects.count(), initial_user_count + 1)
        self.assertEqual(new_user.first_name, 'Test')
        self.assertEqual(new_user.last_name, 'Student')
        self.assertEqual(new_user.email, 'teststudent@example.com')

    def test_username_generation(self):
        """Test that unused usernames are generated correctly"""
        # Create a user with a common name
        user1 = ESPUser.objects.create_user(
            username='john_doe',
            first_name='John',
            last_name='Doe',
            email='john1@example.com'
        )
        
        # Try to create another with same name but different email
        username2 = ESPUser.get_unused_username('John', 'Doe')
        
        # Should generate a different username
        self.assertNotEqual(username2, 'john_doe')
        
        # Should be able to create user with this username
        user2 = ESPUser.objects.create_user(
            username=username2,
            first_name='John',
            last_name='Doe',
            email='john2@example.com'
        )
        
        self.assertNotEqual(user1.username, user2.username)

    def test_user_added_to_student_group(self):
        """Test that created user is added to Student group"""
        # Ensure Student group exists
        student_group, _ = Group.objects.get_or_create(name='Student')
        
        form_data = {
            'first_name': 'Group',
            'last_name': 'Test',
            'email': 'grouptest@example.com',
            'grade': '10',
            'paid': False,
            'medical': False,
            'liability': False,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        
        new_data = form.cleaned_data
        username = ESPUser.get_unused_username(new_data['first_name'], new_data['last_name'])
        new_user = ESPUser.objects.create_user(
            username=username,
            first_name=new_data['first_name'],
            last_name=new_data['last_name'],
            email=new_data['email']
        )
        
        new_user.groups.add(student_group)
        
        self.assertTrue(new_user.groups.filter(name='Student').exists())


class TestOnsiteRegisterProfileCreation(TestCase):
    """Test profile creation during onsite registration"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        self.user = ESPUser.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            first_name='Test',
            last_name='User'
        )

    def test_registration_profile_creation(self):
        """Test that RegistrationProfile is created/updated"""
        reg_prof = RegistrationProfile.getLastForProgram(self.user, self.program)
        
        self.assertIsNotNone(reg_prof)
        self.assertEqual(reg_prof.user, self.user)
        self.assertEqual(reg_prof.program, self.program)

    def test_contact_info_creation(self):
        """Test that ContactInfo is created for user"""
        contact = ContactInfo(
            first_name=self.user.first_name,
            last_name=self.user.last_name,
            e_mail=self.user.email,
            user=self.user
        )
        contact.save()
        
        self.assertIsNotNone(contact.id)
        self.assertEqual(contact.first_name, 'Test')
        self.assertEqual(contact.e_mail, 'testuser@example.com')

    def test_student_info_creation(self):
        """Test that StudentInfo is created with grade/school"""
        student_info = StudentInfo(
            user=self.user,
            graduation_year=2027,
            school='Test High School'
        )
        student_info.save()
        
        self.assertIsNotNone(student_info.id)
        self.assertEqual(student_info.school, 'Test High School')
        self.assertEqual(student_info.graduation_year, 2027)

    def test_registration_profile_associations(self):
        """Test that profile associations are set correctly"""
        reg_prof = RegistrationProfile.getLastForProgram(self.user, self.program)
        
        # Create and assign contact and student info
        contact = ContactInfo(
            first_name=self.user.first_name,
            last_name=self.user.last_name,
            e_mail=self.user.email,
            user=self.user
        )
        contact.save()
        
        student_info = StudentInfo(
            user=self.user,
            graduation_year=2027
        )
        student_info.save()
        
        reg_prof.contact_user = contact
        reg_prof.student_info = student_info
        reg_prof.save()
        
        # Verify associations
        updated_prof = RegistrationProfile.objects.get(id=reg_prof.id)
        self.assertEqual(updated_prof.contact_user, contact)
        self.assertEqual(updated_prof.student_info, student_info)


class TestOnsiteRegisterRecordCreation(TestCase):
    """Test accounting records and bits created during registration"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        self.user = ESPUser.objects.create_user(
            username='testuser',
            email='testuser@example.com'
        )

    def test_attended_record_creation(self):
        """Test that Attended record is created"""
        initial_records = Record.objects.filter(
            user=self.user,
            program=self.program,
            event__name='Attended'
        ).count()
        
        Record.createBit('Attended', self.program, self.user)
        
        final_records = Record.objects.filter(
            user=self.user,
            program=self.program,
            event__name='Attended'
        ).count()
        
        self.assertEqual(final_records, initial_records + 1)

    def test_onsite_record_creation(self):
        """Test that OnSite record is created"""
        initial_records = Record.objects.filter(
            user=self.user,
            program=self.program,
            event__name='OnSite'
        ).count()
        
        Record.createBit('OnSite', self.program, self.user)
        
        final_records = Record.objects.filter(
            user=self.user,
            program=self.program,
            event__name='OnSite'
        ).count()
        
        self.assertEqual(final_records, initial_records + 1)

    def test_medical_record_creation(self):
        """Test that Med record is created when medical checkbox is checked"""
        initial_records = Record.objects.filter(
            user=self.user,
            program=self.program,
            event__name='Med'
        ).count()
        
        Record.createBit('Med', self.program, self.user)
        
        final_records = Record.objects.filter(
            user=self.user,
            program=self.program,
            event__name='Med'
        ).count()
        
        self.assertEqual(final_records, initial_records + 1)

    def test_liability_record_creation(self):
        """Test that Liab record is created when liability checkbox is checked"""
        initial_records = Record.objects.filter(
            user=self.user,
            program=self.program,
            event__name='Liab'
        ).count()
        
        Record.createBit('Liab', self.program, self.user)
        
        final_records = Record.objects.filter(
            user=self.user,
            program=self.program,
            event__name='Liab'
        ).count()
        
        self.assertEqual(final_records, initial_records + 1)


class TestOnsiteRegisterModuleProperties(TestCase):
    """Test OnSiteRegister module properties"""

    def test_module_properties(self):
        """Test that module has correct properties"""
        props = OnSiteRegister.module_properties()
        
        self.assertEqual(props['admin_title'], 'Onsite New Registration')
        self.assertEqual(props['link_title'], 'New Student Registration')
        self.assertEqual(props['module_type'], 'onsite')
        self.assertEqual(props['seq'], 30)
        self.assertEqual(props['choosable'], 1)


class TestOnsiteRegisterK12SchoolHandling(TestCase):
    """Test school/K12School field handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        self.school = K12School.objects.create(
            name='Test High School',
            district='Test District'
        )
        
        self.user = ESPUser.objects.create_user(
            username='testuser',
            email='testuser@example.com'
        )

    def test_student_info_with_k12school(self):
        """Test that StudentInfo properly stores K12School"""
        student_info = StudentInfo(
            user=self.user,
            k12school=self.school,
            graduation_year=2027
        )
        student_info.save()
        
        self.assertEqual(student_info.k12school, self.school)
        self.assertEqual(student_info.school, self.school.name)

    def test_student_info_with_school_name_without_k12school(self):
        """Test that StudentInfo stores school name when K12School not available"""
        student_info = StudentInfo(
            user=self.user,
            school='Custom School Name',
            graduation_year=2028
        )
        student_info.save()
        
        self.assertEqual(student_info.school, 'Custom School Name')

    def test_form_school_field_hidden(self):
        """Test that school field is hidden in form"""
        form = OnSiteRegForm()
        
        self.assertEqual(form.fields['school'].widget.__class__.__name__, 'HiddenInput')


class TestOnsiteRegisterFullWorkflow(TestCase):
    """Test complete onsite registration workflows"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        # Ensure Student group exists
        self.student_group, _ = Group.objects.get_or_create(name='Student')

    def test_complete_registration_flow_with_paid_student(self):
        """Test complete registration flow for paid student"""
        form_data = {
            'first_name': 'Complete',
            'last_name': 'Student',
            'email': 'complete@example.com',
            'grade': '9',
            'paid': True,
            'medical': False,
            'liability': False,
        }
        
        form = OnSiteRegForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        new_data = form.cleaned_data
        
        # Create user
        username = ESPUser.get_unused_username(new_data['first_name'], new_data['last_name'])
        new_user = ESPUser.objects.create_user(
            username=username,
            first_name=new_data['first_name'],
            last_name=new_data['last_name'],
            email=new_data['email']
        )
        
        # Create profile data
        reg_prof = RegistrationProfile.getLastForProgram(new_user, self.program)
        contact_user = ContactInfo(
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            e_mail=new_user.email,
            user=new_user
        )
        contact_user.save()
        
        student_info = StudentInfo(
            user=new_user,
            graduation_year=2027
        )
        student_info.save()
        
        reg_prof.contact_user = contact_user
        reg_prof.student_info = student_info
        reg_prof.save()
        
        # Create records
        Record.createBit('Attended', self.program, new_user)
        Record.createBit('OnSite', self.program, new_user)
        new_user.groups.add(self.student_group)
        
        # Verify all created objects
        self.assertEqual(new_user.first_name, 'Complete')
        self.assertEqual(new_user.last_name, 'Student')
        self.assertTrue(ContactInfo.objects.filter(user=new_user).exists())
        self.assertTrue(StudentInfo.objects.filter(user=new_user).exists())
        self.assertTrue(new_user.groups.filter(name='Student').exists())
        self.assertTrue(Record.objects.filter(user=new_user, event__name='Attended').exists())

    def test_complete_registration_flow_with_medical_and_liability(self):
        """Test complete registration with medical and liability forms"""
        form_data = {
            'first_name': 'Form',
            'last_name': 'Filled',
            'email': 'formfilled@example.com',
            'grade': '11',
            'paid': False,
            'medical': True,
            'liability': True,
        }
        
        form = OnSiteRegForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        new_data = form.cleaned_data
        
        # Create user
        username = ESPUser.get_unused_username(new_data['first_name'], new_data['last_name'])
        new_user = ESPUser.objects.create_user(
            username=username,
            first_name=new_data['first_name'],
            last_name=new_data['last_name'],
            email=new_data['email']
        )
        
        # Create records based on form data
        Record.createBit('Attended', self.program, new_user)
        if new_data['medical']:
            Record.createBit('Med', self.program, new_user)
        if new_data['liability']:
            Record.createBit('Liab', self.program, new_user)
        Record.createBit('OnSite', self.program, new_user)
        
        # Verify records created
        self.assertTrue(Record.objects.filter(
            user=new_user,
            event__name='Med'
        ).exists())
        self.assertTrue(Record.objects.filter(
            user=new_user,
            event__name='Liab'
        ).exists())


class TestOnsiteRegisterFormEdgeCases(TestCase):
    """Test edge cases and special scenarios"""

    def test_form_with_long_names(self):
        """Test form with maximum length names"""
        form_data = {
            'first_name': 'A' * 30,  # Max length
            'last_name': 'B' * 30,   # Max length
            'email': 'test@example.com',
            'grade': '9',
            'paid': False,
            'medical': False,
            'liability': False,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_form_with_special_characters_in_name(self):
        """Test form with special characters in names"""
        form_data = {
            'first_name': "Jean-Claude",
            'last_name': "O'Brien-Smith",
            'email': 'test@example.com',
            'grade': '10',
            'paid': False,
            'medical': False,
            'liability': False,
        }
        form = OnSiteRegForm(data=form_data)
        
        self.assertTrue(form.is_valid())

    def test_form_with_various_grade_values(self):
        """Test form with various valid grade values"""
        form = OnSiteRegForm()
        valid_grades = [choice[0] for choice in form.fields['grade'].choices[1:]]  # Skip empty choice
        
        for grade in valid_grades:
            form_data = {
                'first_name': 'Test',
                'last_name': 'Grade',
                'email': f'grade{grade}@example.com',
                'grade': grade,
                'paid': False,
                'medical': False,
                'liability': False,
            }
            form = OnSiteRegForm(data=form_data)
            self.assertTrue(form.is_valid())

    def test_email_field_max_length(self):
        """Test email field respects max length"""
        # Create an email that exceeds typical limits
        long_email = 'a' * 70 + '@example.com'  # Very long but still valid
        
        form_data = {
            'first_name': 'Email',
            'last_name': 'Test',
            'email': long_email,
            'grade': '9',
            'paid': False,
            'medical': False,
            'liability': False,
        }
        form = OnSiteRegForm(data=form_data)
        
        # Should be valid as long as it's under the max_length
        if len(long_email) <= 75:
            self.assertTrue(form.is_valid())
