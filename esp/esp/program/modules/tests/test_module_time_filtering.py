"""Tests for the time-filtering behaviour added to Program.getModules().

Verifies that non-admin users only see modules whose ``start_date`` /
``end_date`` window includes the current moment, while admins and
internal callers (user=None) bypass the filter entirely.
"""

from datetime import datetime, timedelta

from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest


class TestModuleTimeFiltering(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()

        self.student = self.students[0]
        self.admin = self.admins[0]

        now = datetime.now()
        self.past = now - timedelta(days=1)
        self.future = now + timedelta(days=1)

        # ProgramFrameworkTest provisions ProgramModule rows and links
        # them via the M2M, but ProgramModuleObj rows are created
        # lazily by getFromProgModule().  Mirror the pattern used by
        # test_expirable_module.py to force creation.
        mod = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list(
                'id', flat=True
            )
        ).first()
        self.pmo = ProgramModuleObj.getFromProgModule(
            self.program, mod
        )

    # -- helpers -----------------------------------------------------------

    def _module_ids(self, user):
        """Return set of ProgramModuleObj PKs from getModules()."""
        return {m.id for m in self.program.getModules(user=user)}

    # -- student visibility ------------------------------------------------

    def test_active_module_visible_to_student(self):
        """Module inside its time window is visible to students."""
        self.pmo.start_date = self.past
        self.pmo.end_date = self.future
        self.pmo.save()

        self.assertIn(self.pmo.id, self._module_ids(self.student))

    def test_null_dates_module_visible_to_student(self):
        """Module with no dates (always valid) is visible to students."""
        self.pmo.start_date = None
        self.pmo.end_date = None
        self.pmo.save()

        self.assertIn(self.pmo.id, self._module_ids(self.student))

    def test_expired_module_hidden_from_student(self):
        """Module whose end_date has passed is hidden from students."""
        self.pmo.start_date = None
        self.pmo.end_date = self.past
        self.pmo.save()

        self.assertNotIn(self.pmo.id, self._module_ids(self.student))

    def test_future_module_hidden_from_student(self):
        """Module whose start_date is in the future is hidden."""
        self.pmo.start_date = self.future
        self.pmo.end_date = None
        self.pmo.save()

        self.assertNotIn(self.pmo.id, self._module_ids(self.student))

    # -- admin visibility --------------------------------------------------

    def test_expired_module_visible_to_admin(self):
        """Admins bypass time filtering and see expired modules."""
        self.pmo.start_date = None
        self.pmo.end_date = self.past
        self.pmo.save()

        self.assertIn(self.pmo.id, self._module_ids(self.admin))

    def test_future_module_visible_to_admin(self):
        """Admins bypass time filtering and see future modules."""
        self.pmo.start_date = self.future
        self.pmo.end_date = None
        self.pmo.save()

        self.assertIn(self.pmo.id, self._module_ids(self.admin))

    # -- internal / no-user visibility -------------------------------------

    def test_no_user_returns_all_modules(self):
        """Internal calls (user=None) bypass filtering entirely."""
        self.pmo.start_date = None
        self.pmo.end_date = self.past
        self.pmo.save()

        self.assertIn(self.pmo.id, self._module_ids(None))

        self.pmo.start_date = self.future
        self.pmo.end_date = None
        self.pmo.save()

        self.assertIn(self.pmo.id, self._module_ids(None))
