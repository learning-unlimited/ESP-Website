from datetime import datetime, timedelta

from django.test import TestCase

from esp.cal.models import Event, EventType
from esp.program.models import Program, VolunteerRequest
from esp.program.modules.forms.volunteer import VolunteerOfferForm
from esp.program.modules.handlers.volunteersignup import VolunteerSignup
from esp.tagdict.models import Tag


class VolunteerSignupTestCase(TestCase):
    def setUp(self):
        # Create a basic Program fixture
        self.program = Program.objects.create(
            name='Test Volunteer Program',
            grade_min=7,
            grade_max=12,
        )

        # Create required EventType
        self.volunteer_event_type, _ = EventType.objects.get_or_create(
            description='Volunteer'
        )

        # Create a valid Event linked to program
        self.event = Event.objects.create(
            program=self.program,
            start=datetime.now(),
            end=datetime.now() + timedelta(hours=2),
            event_type=self.volunteer_event_type,
            short_description='Volunteer Shift',
            description='Test Volunteer Shift Description',
        )

        # Create Tag and VolunteerRequest needed for VolunteerOfferForm choices
        self.tag = Tag.objects.create(key='general_volunteer', value='General Volunteer')
        self.volunteer_request = VolunteerRequest.objects.create(
            program=self.program,
            tag=self.tag,
            event=self.event,
            num_requested=5,
        )

        # Initialize the handler module
        self.signup_module = VolunteerSignup(self.program)

    def test_module_properties(self):
        """Verify basic VolunteerSignup module attributes"""
        self.assertTrue(hasattr(self.signup_module, 'program'))
        self.assertEqual(self.signup_module.program.name, 'Test Volunteer Program')

    def test_volunteer_offer_form_validation(self):
        """Verify VolunteerOfferForm validates with complete data"""
        form_data = {
            'name': 'Janvi Kapoor',
            'email': 'janvi@example.com',
            'phone': '1234567890',
            'requests': [self.volunteer_request.id],
            'comments': 'Happy to help with volunteer tasks!',
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
