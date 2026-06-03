"""Tests for the ExpirableModel integration on ProgramModuleObj.

Verifies that ``ProgramModuleObj`` correctly inherits temporal behaviour
(``start_date`` / ``end_date``, ``is_valid()``, ``valid_objects()``)
from ``ExpirableModel`` after the Phase-1 migration.
"""

from datetime import datetime, timedelta
from django.utils import timezone

from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest


class ProgramModuleObjExpirableTest(ProgramFrameworkTest):
    """Verify that ProgramModuleObj temporal fields work correctly."""

    def setUp(self):
        super().setUp()
        # Create a few modules for the program so we can test them
        modules = ProgramModule.objects.all()[:3]
        self.pmo = ProgramModuleObj.getFromProgModule(self.program, modules[0])
        self.pmo2 = ProgramModuleObj.getFromProgModule(self.program, modules[1])
        self.pmo3 = ProgramModuleObj.getFromProgModule(self.program, modules[2])

    # ------------------------------------------------------------------
    # is_valid() tests
    # ------------------------------------------------------------------

    def test_null_dates_is_valid(self):
        """A module with no start/end date is always considered valid."""
        self.pmo.start_date = None
        self.pmo.end_date = None
        self.pmo.save()
        self.assertTrue(self.pmo.is_valid())

    def test_future_start_is_invalid(self):
        """A module whose start_date is in the future is not yet valid."""
        self.pmo.start_date = timezone.now() + timedelta(days=30)
        self.pmo.end_date = None
        self.pmo.save()
        self.assertFalse(self.pmo.is_valid())

    def test_past_end_is_invalid(self):
        """A module whose end_date is in the past is no longer valid."""
        self.pmo.start_date = None
        self.pmo.end_date = timezone.now() - timedelta(days=1)
        self.pmo.save()
        self.assertFalse(self.pmo.is_valid())

    def test_active_window_is_valid(self):
        """A module currently between its start and end date is valid."""
        self.pmo.start_date = timezone.now() - timedelta(days=1)
        self.pmo.end_date = timezone.now() + timedelta(days=30)
        self.pmo.save()
        self.assertTrue(self.pmo.is_valid())

    # ------------------------------------------------------------------
    # valid_objects() queryset test
    # ------------------------------------------------------------------

    def test_valid_objects_filters_correctly(self):
        """valid_objects() should exclude expired and future modules."""
        all_pmos = [self.pmo, self.pmo2, self.pmo3]

        # Make the first module expired
        expired = all_pmos[0]
        expired.end_date = timezone.now() - timedelta(days=1)
        expired.start_date = None
        expired.save()

        # Make the second module future
        future = all_pmos[1]
        future.start_date = timezone.now() + timedelta(days=30)
        future.end_date = None
        future.save()

        # Ensure the rest have null dates (always valid)
        for pmo in all_pmos[2:]:
            pmo.start_date = None
            pmo.end_date = None
            pmo.save()

        valid_ids = set(
            ProgramModuleObj.valid_objects()
            .filter(program=self.program)
            .values_list('id', flat=True)
        )

        self.assertNotIn(expired.id, valid_ids,
                         "Expired module should not appear in valid_objects()")
        self.assertNotIn(future.id, valid_ids,
                         "Future module should not appear in valid_objects()")

        # All remaining modules should be valid
        for pmo in all_pmos[2:]:
            self.assertIn(pmo.id, valid_ids,
                          f"Module {pmo.id} with null dates should be in valid_objects()")
