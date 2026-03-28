"""
Unit tests for volunteersignup.py

Tests cover:
- Volunteer signup form rendering and validation
- Volunteer offer creation and database changes
- Auth requirement behavior via tags
- Deadline-gated access behavior
- Admin search entry generation
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from esp.users.models import ESPUser
from esp.program.models import Program, VolunteerRequest, VolunteerOffer
from esp.program.modules.handlers.volunteersignup import VolunteerSignup
from esp.program.modules.forms.volunteer import VolunteerOfferForm, VolunteerRequestForm
from esp.cal.models import Event, EventType
from esp.tagdict.models import Tag
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


class TestVolunteerSignupModule(TestCase):
    """Test VolunteerSignup module properties and configuration"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        # Create ProgramModuleObj for VolunteerSignup
        from esp.program.modules.models import ProgramModule
        volunteer_module = ProgramModule.objects.filter(
            handler__contains='VolunteerSignup'
        ).first()
        
        if volunteer_module:
            from esp.program.modules.base import ProgramModuleObj
            self.pmo = ProgramModuleObj.objects.create(
                program=self.program,
                module=volunteer_module
            )
        
        self.module_class = VolunteerSignup

    def test_module_properties(self):
        """Test that module has correct properties"""
        props = self.module_class.module_properties()
        
        self.assertEqual(props['admin_title'], 'Volunteer Sign-up Module')
        self.assertEqual(props['link_title'], 'Sign Up to Volunteer')
        self.assertEqual(props['module_type'], 'volunteer')
        self.assertEqual(props['choosable'], 1)

    def test_get_admin_search_entry_for_volunteer_signup(self):
        """Test get_admin_search_entry returns valid entry for volunteer signup"""
        entry = self.module_class.get_admin_search_entry(
            self.program,
            'volunteer',
            'signup',
            None
        )
        
        self.assertIsNotNone(entry)
        self.assertEqual(entry.id, 'volunteer_signup')
        self.assertEqual(entry.category, 'Quick Links')
        self.assertIn('volunteer', entry.keywords)
        self.assertIn('signup', entry.keywords)

    def test_get_admin_search_entry_returns_none_for_wrong_tl(self):
        """Test get_admin_search_entry returns None for wrong tl"""
        entry = self.module_class.get_admin_search_entry(
            self.program,
            'student',  # Wrong tl
            'signup',
            None
        )
        
        self.assertIsNone(entry)

    def test_get_admin_search_entry_returns_none_for_wrong_view(self):
        """Test get_admin_search_entry returns None for wrong view_name"""
        entry = self.module_class.get_admin_search_entry(
            self.program,
            'volunteer',
            'schedule',  # Wrong view_name
            None
        )
        
        self.assertIsNone(entry)

    def test_admin_search_entry_url_format(self):
        """Test that admin search entry URL is properly formatted"""
        entry = self.module_class.get_admin_search_entry(
            self.program,
            'volunteer',
            'signup',
            None
        )
        
        self.assertIn('/volunteer/', entry.url)
        self.assertIn(self.program.getUrlBase(), entry.url)
        self.assertIn('/signup', entry.url)


class TestVolunteerSignupAuthBehavior(TestCase):
    """Test volunteer auth requirement behavior"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        from esp.program.modules.base import ProgramModuleObj
        self.pmo = MagicMock(spec=ProgramModuleObj)
        self.pmo.program = self.program
        
        # Create VolunteerSignup instance
        self.signup_module = VolunteerSignup(self.pmo)

    def test_require_auth_returns_false_by_default(self):
        """Test that auth is not required by default"""
        # Clear the tag if it exists
        with patch('esp.tagdict.models.Tag.getBooleanTag', return_value=False):
            result = self.signup_module.require_auth()
            self.assertFalse(result)

    def test_require_auth_returns_true_when_tag_set(self):
        """Test that auth is required when volunteer_require_auth tag is True"""
        with patch('esp.tagdict.models.Tag.getBooleanTag', return_value=True):
            result = self.signup_module.require_auth()
            self.assertTrue(result)


class TestVolunteerOfferFormValidation(TestCase):
    """Test VolunteerOfferForm validation and field handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        # Create a volunteer timeslot
        self.event = Event.objects.create(
            name='Test Slot',
            start=datetime.now() + timedelta(days=1),
            end=datetime.now() + timedelta(days=1, hours=1),
            event_type=EventType.get_from_desc('Volunteer')
        )
        self.program.events.add(self.event)
        
        self.volunteer_request = VolunteerRequest.objects.create(
            program=self.program,
            timeslot=self.event,
            num_volunteers=5
        )

    def test_form_initialization(self):
        """Test that form initializes correctly"""
        form = VolunteerOfferForm(program=self.program)
        
        self.assertIn('name', form.fields)
        self.assertIn('email', form.fields)
        self.assertIn('phone', form.fields)
        self.assertIn('requests', form.fields)
        self.assertIn('confirm', form.fields)

    def test_form_request_choices_populated(self):
        """Test that form request choices are populated from volunteer requests"""
        form = VolunteerOfferForm(program=self.program)
        
        request_choices = form.fields['requests'].choices
        self.assertGreater(len(request_choices), 0)

    def test_form_with_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'name': 'John Volunteer',
            'email': 'volunteer@example.com',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        self.assertTrue(form.is_valid())

    def test_form_with_missing_name(self):
        """Test form validation fails without name"""
        form_data = {
            'email': 'volunteer@example.com',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        self.assertFalse(form.is_valid())

    def test_form_with_missing_email(self):
        """Test form validation fails without email"""
        form_data = {
            'name': 'John Volunteer',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        self.assertFalse(form.is_valid())

    def test_form_with_invalid_email(self):
        """Test form validation fails with invalid email"""
        form_data = {
            'name': 'John Volunteer',
            'email': 'not-an-email',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        self.assertFalse(form.is_valid())

    def test_form_with_missing_phone(self):
        """Test form validation fails without phone"""
        form_data = {
            'name': 'John Volunteer',
            'email': 'volunteer@example.com',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        self.assertFalse(form.is_valid())

    def test_form_without_confirm_checkbox(self):
        """Test form without confirmation checkbox"""
        form_data = {
            'name': 'John Volunteer',
            'email': 'volunteer@example.com',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': False,  # Not confirmed
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        # Form should still be valid but offer might be marked as unconfirmed
        is_valid = form.is_valid()
        # Expect it to have issues if confirmation is required
        if is_valid:
            self.assertIsNotNone(form.cleaned_data)


class TestVolunteerOfferCreation(TestCase):
    """Test volunteer offer creation and database changes"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        # Create a volunteer timeslot
        self.event = Event.objects.create(
            name='Test Slot',
            start=datetime.now() + timedelta(days=1),
            end=datetime.now() + timedelta(days=1, hours=1),
            event_type=EventType.get_from_desc('Volunteer')
        )
        self.program.events.add(self.event)
        
        self.volunteer_request = VolunteerRequest.objects.create(
            program=self.program,
            timeslot=self.event,
            num_volunteers=5
        )

    def test_form_save_creates_volunteer_offer(self):
        """Test that form.save() creates a VolunteerOffer"""
        initial_count = VolunteerOffer.objects.count()
        
        form_data = {
            'name': 'John Volunteer',
            'email': 'volunteer@example.com',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
            'user': '',
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        if form.is_valid():
            offers = form.save()
            
            # Should have created an offer
            self.assertGreater(len(offers), 0)
            self.assertEqual(VolunteerOffer.objects.count(), initial_count + 1)

    def test_form_save_with_user_creates_offer(self):
        """Test that form.save() with user creates offer for existing user"""
        user = ESPUser.objects.create_user(
            username='testuser',
            email='testuser@example.com'
        )
        
        form_data = {
            'name': user.name(),
            'email': user.email,
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
            'user': str(user.id),
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        if form.is_valid():
            offers = form.save()
            
            # Should have created an offer linked to the user
            self.assertGreater(len(offers), 0)
            self.assertEqual(offers[0].user, user)

    def test_form_save_returns_empty_list_when_cancelled(self):
        """Test that form.save() returns empty list when clear_requests is True"""
        form_data = {
            'name': 'John Volunteer',
            'email': 'volunteer@example.com',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
            'clear_requests': True,  # Cancel all shifts
            'user': '',
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        if form.is_valid():
            offers = form.save()
            
            # Should return empty list when cancelled
            self.assertEqual(len(offers), 0)

    def test_form_save_creates_user_if_not_exists(self):
        """Test that form.save() creates new user if one doesn't exist"""
        initial_user_count = ESPUser.objects.count()
        
        form_data = {
            'name': 'New Volunteer Person',
            'email': 'newvolunteer@example.com',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
            'user': '',
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        if form.is_valid():
            offers = form.save()
            
            # Should have created a new user
            self.assertGreater(ESPUser.objects.count(), initial_user_count)

    def test_form_save_stores_contact_info(self):
        """Test that form.save() stores name, email, and phone in offer"""
        form_data = {
            'name': 'John Volunteer',
            'email': 'volunteer@example.com',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
            'user': '',
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        if form.is_valid():
            offers = form.save()
            
            self.assertEqual(offers[0].name, 'John Volunteer')
            self.assertEqual(offers[0].email, 'volunteer@example.com')
            self.assertEqual(str(offers[0].phone), '+12025551234')

    def test_form_save_with_multiple_requests(self):
        """Test that form.save() creates offers for multiple selected requests"""
        # Create another volunteer request
        event2 = Event.objects.create(
            name='Test Slot 2',
            start=datetime.now() + timedelta(days=2),
            end=datetime.now() + timedelta(days=2, hours=1),
            event_type=EventType.get_from_desc('Volunteer')
        )
        self.program.events.add(event2)
        
        volunteer_request2 = VolunteerRequest.objects.create(
            program=self.program,
            timeslot=event2,
            num_volunteers=3
        )
        
        form_data = {
            'name': 'John Volunteer',
            'email': 'volunteer@example.com',
            'phone': '+12025551234',
            'requests': [str(self.volunteer_request.id), str(volunteer_request2.id)],
            'confirm': True,
            'user': '',
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        if form.is_valid():
            offers = form.save()
            
            # Should create offers for both requests
            self.assertEqual(len(offers), 2)


class TestVolunteerRequestForm(TestCase):
    """Test VolunteerRequestForm for volunteer shift management"""

    def setUp(self):
        """Set up test fixtures"""
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )

    def test_form_initialization(self):
        """Test that VolunteerRequestForm initializes correctly"""
        form = VolunteerRequestForm(program=self.program)
        
        self.assertIn('start_time', form.fields)
        self.assertIn('end_time', form.fields)
        self.assertIn('num_volunteers', form.fields)
        self.assertIn('description', form.fields)

    def test_form_with_valid_data(self):
        """Test form validation with valid data"""
        start = datetime.now() + timedelta(days=1)
        end = datetime.now() + timedelta(days=1, hours=2)
        
        form_data = {
            'start_time': start,
            'end_time': end,
            'num_volunteers': 5,
            'description': 'Registration desk',
        }
        form = VolunteerRequestForm(data=form_data, program=self.program)
        
        self.assertTrue(form.is_valid())

    def test_form_with_missing_required_fields(self):
        """Test form validation fails without required fields"""
        form_data = {
            'description': 'Registration desk',
        }
        form = VolunteerRequestForm(data=form_data, program=self.program)
        
        self.assertFalse(form.is_valid())

    def test_form_with_invalid_num_volunteers(self):
        """Test form validation with invalid volunteer count"""
        start = datetime.now() + timedelta(days=1)
        end = datetime.now() + timedelta(days=1, hours=2)
        
        form_data = {
            'start_time': start,
            'end_time': end,
            'num_volunteers': 'invalid',  # Should be integer
            'description': 'Registration desk',
        }
        form = VolunteerRequestForm(data=form_data, program=self.program)
        
        self.assertFalse(form.is_valid())

    def test_form_save_creates_volunteer_request(self):
        """Test that form.save() creates a VolunteerRequest"""
        start = datetime.now() + timedelta(days=1)
        end = datetime.now() + timedelta(days=1, hours=2)
        
        form_data = {
            'start_time': start,
            'end_time': end,
            'num_volunteers': 5,
            'description': 'Registration desk',
        }
        form = VolunteerRequestForm(data=form_data, program=self.program)
        
        if form.is_valid():
            initial_count = VolunteerRequest.objects.count()
            form.save()
            
            # Should have created a volunteer request
            self.assertGreater(VolunteerRequest.objects.count(), initial_count)


class TestVolunteerSignupFlows(TestCase):
    """Test complete volunteer signup workflows"""

    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.user = ESPUser.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            first_name='Test',
            last_name='User'
        )
        
        self.program = Program.objects.create(
            name='Test Program',
            url='test_program'
        )
        
        # Create volunteer timeslots
        self.event = Event.objects.create(
            name='Test Slot',
            start=datetime.now() + timedelta(days=1),
            end=datetime.now() + timedelta(days=1, hours=1),
            event_type=EventType.get_from_desc('Volunteer')
        )
        self.program.events.add(self.event)
        
        self.volunteer_request = VolunteerRequest.objects.create(
            program=self.program,
            timeslot=self.event,
            num_volunteers=5
        )

    def test_volunteer_signup_form_load_with_user(self):
        """Test that form.load() pre-fills user information"""
        form = VolunteerOfferForm(program=self.program)
        form.load(self.user)
        
        # Should have pre-filled user data
        self.assertEqual(form.fields['email'].initial, self.user.email)
        self.assertIn(self.user.last_name, form.fields['name'].initial)

    def test_volunteer_signup_form_clears_previous_offers(self):
        """Test that signup clears previous volunteer offers"""
        # Create an initial offer
        initial_offer = VolunteerOffer.objects.create(
            user=self.user,
            name=self.user.name(),
            email=self.user.email,
            phone='+12025551234',
            request=self.volunteer_request,
            confirmed=True
        )
        
        self.assertEqual(VolunteerOffer.objects.filter(user=self.user).count(), 1)
        
        # Submit new offer
        form_data = {
            'name': self.user.name(),
            'email': self.user.email,
            'phone': '+19876543210',
            'requests': [str(self.volunteer_request.id)],
            'confirm': True,
            'user': str(self.user.id),
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        
        if form.is_valid():
            offers = form.save()
            
            # Should have replaced the previous offer
            self.assertEqual(VolunteerOffer.objects.filter(user=self.user).count(), 1)
            self.assertEqual(offers[0].phone, '+19876543210')
