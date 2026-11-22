from datetime import datetime, timedelta

from django.test import TestCase

from esp.cal.models import Event, EventType
from esp.program.models import Program, VolunteerOffer, VolunteerRequest
from esp.program.modules.forms.volunteer import VolunteerOfferForm
from esp.program.modules.handlers.volunteersignup import VolunteerSignup
from esp.tagdict.models import Tag
from esp.users.models import ESPUser


class VolunteerSignupTestCase(TestCase):
    def setUp(self):
        # Create a basic Program fixture
        self.program = Program.objects.create(
            name='Test Volunteer Program',
            url='VolunteerTest/Main',
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

        # Set tag using official Tag.setTag as explicitly requested by maintainer
        Tag.setTag('general_volunteer', value='General Volunteer')

        # Create VolunteerRequest with verified model fields
        self.volunteer_request = VolunteerRequest.objects.create(
            program=self.program,
            timeslot=self.event,
            num_volunteers=5,
        )

        # Initialize the handler module
        self.signup_module = VolunteerSignup(self.program)

    def test_module_properties(self):
        """Verify basic VolunteerSignup module attributes"""
        self.assertIsNotNone(self.signup_module)

    def test_volunteer_offer_form_validation(self):
        """Verify VolunteerOfferForm validates with complete data"""
        form_data = {
            'name': 'Janvi Kapoor',
            'email': 'janvi@example.com',
            'phone': '(201) 555-0123',
            'requests': [self.volunteer_request.id],
            'comments': 'Happy to help with volunteer tasks!',
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_save_scoped_to_current_program(self):
        """Verify saving volunteer shifts replaces offers only in the active program."""
        other_program = Program.objects.create(
            name='Other Volunteer Program',
            url='VolunteerTest/Other1',
            grade_min=7,
            grade_max=12,
        )
        other_event = Event.objects.create(
            program=other_program,
            start=datetime.now() + timedelta(days=1),
            end=datetime.now() + timedelta(days=1, hours=2),
            event_type=self.volunteer_event_type,
            short_description='Other Shift',
            description='Other Program Volunteer Shift',
        )
        other_request = VolunteerRequest.objects.create(
            program=other_program,
            timeslot=other_event,
            num_volunteers=3,
        )

        second_event = Event.objects.create(
            program=self.program,
            start=datetime.now() + timedelta(hours=3),
            end=datetime.now() + timedelta(hours=5),
            event_type=self.volunteer_event_type,
            short_description='Second Shift',
            description='Second Shift in Self Program',
        )
        second_request = VolunteerRequest.objects.create(
            program=self.program,
            timeslot=second_event,
            num_volunteers=3,
        )

        user = ESPUser.objects.create_user('voluser1', 'voluser1@example.com')
        user.first_name = 'Volunteer'
        user.last_name = 'One'
        user.save()

        # Existing offers in both other_program and self.program
        other_offer = VolunteerOffer.objects.create(
            request=other_request,
            user=user,
            name=user.name(),
            email=user.email,
            phone='(201) 555-0123',
            confirmed=True,
        )
        initial_self_offer = VolunteerOffer.objects.create(
            request=self.volunteer_request,
            user=user,
            name=user.name(),
            email=user.email,
            phone='(201) 555-0123',
            confirmed=True,
        )

        # Update volunteer shifts for self.program to second_request
        form_data = {
            'user': user.id,
            'name': user.name(),
            'email': user.email,
            'phone': '(201) 555-0123',
            'requests': [second_request.id],
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        form.save()

        # Self program offers updated
        self.assertEqual(
            list(user.getVolunteerOffers(self.program).values_list('request_id', flat=True)),
            [second_request.id],
        )
        self.assertFalse(VolunteerOffer.objects.filter(id=initial_self_offer.id).exists())

        # Other program offer remains intact
        self.assertTrue(VolunteerOffer.objects.filter(id=other_offer.id).exists())
        self.assertEqual(user.getVolunteerOffers(other_program).count(), 1)

    def test_clear_requests_scoped_to_current_program(self):
        """Verify cancelling shifts removes offers only in the active program."""
        other_program = Program.objects.create(
            name='Other Volunteer Program 2',
            url='VolunteerTest/Other2',
            grade_min=7,
            grade_max=12,
        )
        other_event = Event.objects.create(
            program=other_program,
            start=datetime.now() + timedelta(days=2),
            end=datetime.now() + timedelta(days=2, hours=2),
            event_type=self.volunteer_event_type,
            short_description='Other Shift 2',
            description='Other Shift Description 2',
        )
        other_request = VolunteerRequest.objects.create(
            program=other_program,
            timeslot=other_event,
            num_volunteers=2,
        )

        user = ESPUser.objects.create_user('voluser2', 'voluser2@example.com')
        user.first_name = 'Volunteer'
        user.last_name = 'Two'
        user.save()

        other_offer = VolunteerOffer.objects.create(
            request=other_request,
            user=user,
            name=user.name(),
            email=user.email,
            phone='(201) 555-0123',
            confirmed=True,
        )
        self_offer = VolunteerOffer.objects.create(
            request=self.volunteer_request,
            user=user,
            name=user.name(),
            email=user.email,
            phone='(201) 555-0123',
            confirmed=True,
        )

        # Clear shifts in self.program
        form_data = {
            'user': user.id,
            'name': user.name(),
            'email': user.email,
            'phone': '(201) 555-0123',
            'clear_requests': True,
            'has_previous_requests': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        result = form.save()
        self.assertEqual(result, [])

        # Self program offers cleared
        self.assertEqual(user.getVolunteerOffers(self.program).count(), 0)
        self.assertFalse(VolunteerOffer.objects.filter(id=self_offer.id).exists())

        # Other program offer remains intact
        self.assertTrue(VolunteerOffer.objects.filter(id=other_offer.id).exists())
        self.assertEqual(user.getVolunteerOffers(other_program).count(), 1)

    def test_anonymous_volunteer_save_and_clear_scoped_to_program(self):
        """Verify unauthenticated volunteer operations are scoped by program and contact info."""
        other_program = Program.objects.create(
            name='Other Volunteer Program 3',
            url='VolunteerTest/Other3',
            grade_min=7,
            grade_max=12,
        )
        other_event = Event.objects.create(
            program=other_program,
            start=datetime.now() + timedelta(days=3),
            end=datetime.now() + timedelta(days=3, hours=2),
            event_type=self.volunteer_event_type,
            short_description='Other Shift 3',
            description='Other Shift Description 3',
        )
        other_request = VolunteerRequest.objects.create(
            program=other_program,
            timeslot=other_event,
            num_volunteers=2,
        )

        anon_name = 'Anon Volunteer'
        anon_email = 'anonvol@example.com'
        anon_phone = '(201) 555-9876'

        other_offer = VolunteerOffer.objects.create(
            request=other_request,
            name=anon_name,
            email=anon_email,
            phone=anon_phone,
            confirmed=True,
        )

        # Sign up in self.program
        form_data = {
            'name': anon_name,
            'email': anon_email,
            'phone': anon_phone,
            'requests': [self.volunteer_request.id],
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        form.save()

        # Other program offer remains intact
        self.assertTrue(VolunteerOffer.objects.filter(id=other_offer.id).exists())
        self.assertEqual(
            VolunteerOffer.objects.filter(email=anon_email, request__program=other_program).count(),
            1,
        )
        self.assertEqual(
            VolunteerOffer.objects.filter(email=anon_email, request__program=self.program).count(),
            1,
        )

        # Cancel shifts in self.program
        clear_data = {
            'name': anon_name,
            'email': anon_email,
            'phone': anon_phone,
            'clear_requests': True,
            'has_previous_requests': True,
        }
        clear_form = VolunteerOfferForm(data=clear_data, program=self.program)
        self.assertTrue(clear_form.is_valid(), msg=f"Form errors: {clear_form.errors}")
        clear_form.save()

        # Self program offer cleared, other program preserved
        self.assertEqual(
            VolunteerOffer.objects.filter(email=anon_email, request__program=self.program).count(),
            0,
        )
        self.assertEqual(
            VolunteerOffer.objects.filter(email=anon_email, request__program=other_program).count(),
            1,
        )

    def test_nonexistent_user_id_does_not_crash(self):
        """Verify invalid user ID in form data falls back gracefully without 500 DoesNotExist."""
        form_data = {
            'user': 9999999,
            'name': 'Fallback Volunteer',
            'email': 'fallback@example.com',
            'phone': '(201) 555-4321',
            'requests': [self.volunteer_request.id],
            'confirm': True,
        }
        form = VolunteerOfferForm(data=form_data, program=self.program)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        offers = form.save()
        self.assertEqual(len(offers), 1)
        self.assertEqual(int(offers[0].request_id), self.volunteer_request.id)
