"""
Tests for esp.context_processors
Source: esp/esp/context_processors.py

Tests context processor functions: media_url, esp_user, email_settings,
program, schoolyear, index_backgrounds, current_site, preload_images.
"""
from django.contrib.auth.models import Group
from django.test import RequestFactory

from esp.context_processors import (
    current_site,
    email_settings,
    esp_user,
    espuserified_request,
    index_backgrounds,
    media_url,
    preload_images,
    program,
    schoolyear,
)
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class MediaUrlTest(TestCase):
    def test_returns_media_url(self):
        factory = RequestFactory()
        request = factory.get('/')
        result = media_url(request)
        self.assertIn('media_url', result)


class EspUserTest(TestCase):
    def test_returns_user_callable(self):
        _setup_roles()
        factory = RequestFactory()
        request = factory.get('/')
        request.user = ESPUser.objects.create_user(
            username='ctxuser', password='password',
        )
        result = esp_user(request)
        self.assertIn('user', result)


class EspuserifiedRequestTest(TestCase):
    def test_returns_request(self):
        factory = RequestFactory()
        request = factory.get('/')
        result = espuserified_request(request)
        self.assertIn('request', result)
        self.assertEqual(result['request'], request)


class EmailSettingsTest(TestCase):
    def test_returns_email_settings(self):
        factory = RequestFactory()
        request = factory.get('/')
        result = email_settings(request)
        self.assertIn('DEFAULT_EMAIL_ADDRESSES', result)
        self.assertIn('EMAIL_HOST_SENDER', result)
        self.assertIn('settings', result)


class ProgramContextTest(TestCase):
    def test_no_program_returns_empty(self):
        factory = RequestFactory()
        request = factory.get('/some/path/')
        result = program(request)
        self.assertEqual(result, {})

    def test_with_request_program(self):
        _setup_roles()
        from esp.program.models import Program as ProgramModel
        prog = ProgramModel.objects.create(grade_min=7, grade_max=12)
        factory = RequestFactory()
        request = factory.get('/')
        request.program = prog
        result = program(request)
        self.assertIn('program', result)
        self.assertEqual(result['program'], prog)


class SchoolyearTest(TestCase):
    def test_returns_schoolyear(self):
        factory = RequestFactory()
        request = factory.get('/some/path/')
        result = schoolyear(request)
        self.assertIn('schoolyear', result)


class IndexBackgroundsTest(TestCase):
    def test_returns_backgrounds_list(self):
        factory = RequestFactory()
        request = factory.get('/')
        result = index_backgrounds(request)
        self.assertIn('backgrounds', result)
        self.assertEqual(len(result['backgrounds']), 3)


class CurrentSiteTest(TestCase):
    def test_returns_current_site(self):
        factory = RequestFactory()
        request = factory.get('/')
        result = current_site(request)
        self.assertIn('current_site', result)


class PreloadImagesTest(TestCase):
    def test_returns_preload_images(self):
        factory = RequestFactory()
        request = factory.get('/')
        result = preload_images(request)
        self.assertIn('preload_images', result)
        self.assertIsInstance(result['preload_images'], list)
