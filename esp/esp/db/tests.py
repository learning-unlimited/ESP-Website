"""Tests for esp.db.fields.AjaxForeignKey.

The Django 2.2 -> 3.2 migration added kwargs to ForeignKey.formfield()
(notably 'blank') that AjaxForeignKeyNewformField (an IntegerField subclass)
does not accept on its own. esp.db.forms pops these before super().__init__()
to avoid a TypeError at form-construction time. These tests cover the
formfield() / render path end-to-end so a future Django bump fails loudly
here if a new kwarg is added to ForeignKey.formfield().
"""
from django.test import TestCase

from esp.users.models import Record


class AjaxForeignKeyFormfieldTest(TestCase):
    """End-to-end coverage of the AjaxForeignKey form-field path."""

    def test_formfield_with_no_extra_kwargs(self):
        """Plain formfield() call returns a working form field."""
        # Record.user is an AjaxForeignKey to ESPUser. This is the same call
        # that ModelForm and admin.ModelAdmin make internally when building
        # a form field for the FK.
        field = Record._meta.get_field('user').formfield()
        self.assertIsNotNone(field)

    def test_formfield_with_django_3_2_kwargs(self):
        """All kwargs ForeignKey.formfield() injects in 3.2 are handled."""
        # Pass each kwarg explicitly so we don't depend on Django's internal
        # defaults to detect a regression if the upstream defaults shift.
        field = Record._meta.get_field('user').formfield(
            limit_choices_to=None,
            blank=True,
            queryset=None,
            to_field_name=None,
        )
        self.assertIsNotNone(field)

    def test_widget_renders_without_error(self):
        """Rendered widget HTML contains the autocomplete machinery."""
        field = Record._meta.get_field('user').formfield()
        # value=None avoids the DB-lookup branch in render(), so the test
        # doesn't depend on any rows existing.
        html = field.widget.render('user', None)
        self.assertIn('autocomplete', html)
        self.assertIn('id_user', html)
