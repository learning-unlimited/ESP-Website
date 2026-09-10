"""Tests for the tags that make previously hard-coded behavior configurable.

Each tag's default must reproduce the old hard-coded behavior, so the
"default" assertions below are the important ones.
"""
from datetime import datetime, timedelta

from django.core.cache import cache
from django.test import TestCase

from esp.cal.models import Event, EventType
from esp.program.models import Program, VolunteerRequest
from esp.program.modules.forms.onsite import OnSiteRegForm
from esp.program.modules.forms.volunteer import VolunteerOfferForm
from esp.tagdict.models import Tag
from esp.users.forms.user_profile import GuardContactForm, StudentProfileForm
from esp.users.models import ESPUser


class CustomizationTagsTestCase(TestCase):
    def setUp(self):
        # Tag reads are memoized in memcached, which is not rolled back with
        # the test transaction, so clear it between tests.
        if hasattr(cache, 'flush_all'):
            cache.flush_all()

        self.program = Program.objects.create(name='Test Program', grade_min=7, grade_max=12)
        event_type, _ = EventType.objects.get_or_create(description='Volunteer')
        timeslot = Event.objects.create(
            program=self.program, start=datetime.now(),
            end=datetime.now() + timedelta(hours=2), event_type=event_type,
            short_description='Shift', description='Test shift',
        )
        VolunteerRequest.objects.create(program=self.program, timeslot=timeslot, num_volunteers=5)

        self.user = ESPUser.objects.create_user(username='student1', email='student1@example.com')
        self.user.makeRole('Student')

    def test_onsite_show_paid_field(self):
        self.assertIn('paid', OnSiteRegForm().fields)
        Tag.setTag('onsite_show_paid_field', value='False')
        self.assertNotIn('paid', OnSiteRegForm().fields)

    def test_student_profile_show_guardian_info(self):
        guard_fields = list(GuardContactForm.declared_fields)
        self.assertTrue(guard_fields)
        for field in guard_fields:
            self.assertIn(field, StudentProfileForm(user=self.user).fields)

        Tag.setTag('student_profile_show_guardian_info', value='False')
        remaining = StudentProfileForm(user=self.user).fields
        for field in guard_fields:
            self.assertNotIn(field, remaining)
        # Unrelated sections are untouched
        self.assertIn('emerg_first_name', remaining)

    def test_volunteer_text_overrides(self):
        Tag.setTag('volunteer_allow_comments', value='True')
        defaults = VolunteerOfferForm(program=self.program).fields
        self.assertNotEqual(defaults['requests'].help_text, 'Pick your shifts')

        Tag.setTag('volunteer_help_text_requests', target=self.program, value='Pick your shifts')
        Tag.setTag('volunteer_label_comments', target=self.program, value='Number of shifts')
        Tag.setTag('volunteer_help_text_confirm', target=self.program, value='I am available')

        fields = VolunteerOfferForm(program=self.program).fields
        self.assertEqual(fields['requests'].help_text, 'Pick your shifts')
        self.assertEqual(fields['comments'].label, 'Number of shifts')
        # The confirm tag supplies text only; the default red styling is kept
        self.assertIn('I am available', fields['confirm'].help_text)
        self.assertIn('color: red', fields['confirm'].help_text)

    def test_volunteer_confirm_text_is_escaped(self):
        Tag.setTag('volunteer_help_text_confirm', target=self.program,
                   value='<script>alert(1)</script>')
        help_text = VolunteerOfferForm(program=self.program).fields['confirm'].help_text
        self.assertNotIn('<script>', help_text)
        self.assertIn('&lt;script&gt;', help_text)

    def test_bigboard_graph_tags(self):
        keys = ('bigboard_graph_drop_beg', 'bigboard_graph_drop_end',
                'bigboard_graph_min_points')
        # Defaults match the values these replaced
        self.assertEqual([int(Tag.getProgramTag(k, self.program)) for k in keys], [4, 0, 5])

        for key, value in zip(keys, ('0', '2', '10')):
            Tag.setTag(key, target=self.program, value=value)
        self.assertEqual([int(Tag.getProgramTag(k, self.program)) for k in keys], [0, 2, 10])
