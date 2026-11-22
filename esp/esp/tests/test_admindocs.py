"""
Tests that the Django admin documentation pages (/admin/doc/) load.

admindocs builds its page context from Django's default admin site, which ESP
doesn't serve. Any app registered there whose label isn't on ESP's own admin
site breaks every admindocs page with NoReverseMatch (django-filebrowser did).
"""

from django.contrib import admin
from django.test import TestCase
from django.urls import get_resolver

from esp.admin import admin_site
from esp.tests.factories import make_user


class AdminDocsTest(TestCase):
    def setUp(self):
        user = make_user('Administrator', username='admindocs_admin')
        user.makeAdmin()
        self.client.force_login(user)

    def test_pages_load(self):
        for url in ['/admin/doc/', '/admin/doc/tags/', '/admin/doc/filters/', '/admin/doc/models/',
                    '/admin/doc/views/', '/admin/doc/models/program.program/', '/admin/doc/bookmarklets/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_default_site_apps_exist_on_esp_site(self):
        # Registration happens when the URLconf runs ESP's admin autodiscover
        get_resolver().url_patterns
        esp_labels = {model._meta.app_label for model in admin_site._registry}
        default_labels = {model._meta.app_label for model in admin.site._registry}
        self.assertEqual(default_labels - esp_labels, set())
