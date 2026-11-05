"""
Behavioral tests for AdminVitals (esp/program/modules/handlers/adminvitals.py).

AdminVitals powers the "Program Vitals" inline template on the admin dashboard.
prepare() must return the context unchanged and never raise, even with
missing/empty dashboard payloads.

Refs: #5130, #3780
"""

from unittest.mock import MagicMock

from esp.program.modules.handlers.adminvitals import AdminVitals, KeyDoesNotExist
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.tests.util import CacheFlushTestCase


class AdminVitalsPropertiesTest(CacheFlushTestCase):
    """Pure unit tests for module_properties / isStep - no DB needed."""

    def test_module_properties_returns_dict(self):
        props = AdminVitals.module_properties()
        self.assertIsInstance(props, dict)

    def test_module_properties_has_required_keys(self):
        props = AdminVitals.module_properties()
        for key in ("admin_title", "link_title", "module_type", "seq", "choosable"):
            self.assertIn(key, props)

    def test_module_properties_values(self):
        props = AdminVitals.module_properties()
        self.assertEqual(props["admin_title"], "Admin Module for Showing Basic Vitals")
        self.assertEqual(props["link_title"], "Program Vitals")
        self.assertEqual(props["module_type"], "manage")
        self.assertEqual(props["inline_template"], "vitals.html")
        self.assertEqual(props["choosable"], 1)

    def test_is_step_is_false(self):
        # isStep is an instance method but does not touch self, so a mock is enough.
        obj = MagicMock(spec=AdminVitals)
        self.assertFalse(AdminVitals.isStep(obj))

    def test_key_does_not_exist_is_exception(self):
        self.assertTrue(issubclass(KeyDoesNotExist, Exception))


class AdminVitalsPrepareTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
    """prepare() must pass context through safely (acceptance criteria for #5130)."""

    def setUp(self):
        super().setUp()
        self.moduleobj = self.get_module_obj("AdminVitals")

    def test_prepare_returns_none_when_no_context(self):
        self.assertIsNone(self.moduleobj.prepare(None))

    def test_prepare_returns_same_context_object(self):
        context = {"foo": "bar"}
        self.assertIs(self.moduleobj.prepare(context), context)

    def test_prepare_with_empty_dict(self):
        context = {}
        self.assertEqual(self.moduleobj.prepare(context), {})

    def test_prepare_with_mock_context_payload(self):
        # Standard Mock context payloads must not raise KeyDoesNotExist
        # or crash the dashboard pipeline.
        context = MagicMock()
        try:
            result = self.moduleobj.prepare(context)
        except KeyDoesNotExist:
            self.fail("prepare() raised KeyDoesNotExist on a Mock context")
        self.assertIs(result, context)

    def test_prepare_does_not_mutate_context(self):
        context = {"prog": self.program, "counts": [1, 2, 3]}
        snapshot = dict(context)
        self.moduleobj.prepare(context)
        self.assertEqual(context, snapshot)
