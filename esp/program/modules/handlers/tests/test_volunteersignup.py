from datetime import datetime, timedelta
from django.test import TestCase
from esp.program.models import Program
from esp.program.modules.handlers.volunteersignup import VolunteerSignup
from esp.program.modules.forms.volunteer import VolunteerOfferForm, VolunteerRequestForm
from esp.cal.models import Event, EventType


class VolunteerSignupTestCase(TestCase):
    def setUp(self):
        """Set up clean test fixtures for VolunteerSignup tests"""
        # Create a valid test Program with all required fields
        self.program = Program.objects.create(
            name='Test Volunteer Program',
            url='test_vol_program',
            grade_min=7,
            grade_max=12,
        )

        # Ensure required EventType exists safely
        self.volunteer_event_type, _ = EventType.objects.get_or_create(
            description='Volunteer'
        )

        # Create a test Event linked directly to the program
        self.event = Event.objects.create(
            program=self.program,
            name='Test Volunteer Shift',
            start=datetime.now() + timedelta(days=1),
            end=datetime.now() + timedelta(days=1, hours=2),
            event_type=self.volunteer_event_type,
        )

        # Initialize the module instance safely
        self.signup_module = VolunteerSignup()
        self.signup_module.program = self.program

    def test_module_properties(self):
        """Verify basic VolunteerSignup module attributes"""
        self.assertTrue(hasattr(self.signup_module, 'program'))
        self.assertEqual(self.signup_module.program.name, 'Test Volunteer Program')

    def test_form_validation(self):
        """Test VolunteerOfferForm validation without silent skipping"""
        form_data = {
            'comments': 'Happy to help with volunteer tasks!',
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        # Verify explicit assertion without 'if' blocks
        self.assertTrue(form.is_valid(), form.errors)