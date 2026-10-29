"""
Tests for esp.db.fields
Source: esp/esp/db/fields.py

Tests AjaxForeignKey custom field.
"""
from django.contrib.auth.models import Group

from esp.accounting.models import Account
from esp.db.fields import AjaxForeignKey
from esp.tests.util import CacheFlushTestCase as TestCase


def _setup_roles():
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


class AjaxForeignKeyTest(TestCase):
    """Test that AjaxForeignKey works as a standard ForeignKey with extras."""

    def setUp(self):
        super().setUp()
        _setup_roles()

    def test_field_is_foreign_key(self):
        """AjaxForeignKey should be a subclass of ForeignKey."""
        from django.db.models import ForeignKey
        self.assertTrue(issubclass(AjaxForeignKey, ForeignKey))

    def test_formfield_returns_field(self):
        """The formfield method should return a form field."""
        # Get an AjaxForeignKey field from an existing model
        from esp.accounting.models import Transfer
        field = Transfer._meta.get_field('user')
        form_field = field.formfield()
        self.assertIsNotNone(form_field)
