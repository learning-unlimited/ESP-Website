from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, RequestFactory

from esp.program.modules.handlers.listgenmodule import ListGenModule
from esp.users.models import PersistentQueryFilter
from esp.middleware import ESPError_NoLog


class ListGenModuleExceptionTests(SimpleTestCase):
    """Regression tests for invalid PersistentQueryFilter IDs in ListGenModule."""

    def setUp(self):
        self.factory = RequestFactory()
        self.module = SimpleNamespace()
        # Mocking self.program which is used in generateList
        self.module.program = SimpleNamespace()
        self.module.program.getLists = lambda x: []
        # Mocking baseDir used for template rendering
        self.module.baseDir = lambda: "program/modules/listgen/"

    def _call_handler(self, handler_fn, params):
        request = self.factory.get("/manage/test", params)
        # Handle the aux_call/needs_admin decorator
        fn = getattr(handler_fn, "method", handler_fn)
        # Calling with arguments expected by most module handlers: self, request, tl, one, two, module, extra, prog
        return fn(self.module, request, "manage", None, None, "listgen", None, self.module.program)

    def test_selectList_old_invalid_numeric_filterid_raises_ESPError(self):
        with patch.object(PersistentQueryFilter, "getFilterFromID", side_effect=PersistentQueryFilter.DoesNotExist):
            with self.assertRaises(ESPError_NoLog) as cm:
                self._call_handler(ListGenModule.selectList_old, {"filterid": "9999"})
            self.assertEqual(str(cm.exception), "The query filter ID given is invalid or has expired.")

    def test_selectList_old_non_numeric_filterid_raises_ESPError(self):
        with patch.object(PersistentQueryFilter, "getFilterFromID", side_effect=AssertionError):
            with self.assertRaises(ESPError_NoLog) as cm:
                self._call_handler(ListGenModule.selectList_old, {"filterid": "abc"})
            self.assertEqual(str(cm.exception), "The query filter ID given is invalid or has expired.")

    def test_generateList_invalid_numeric_filterid_raises_ESPError(self):
        with patch.object(PersistentQueryFilter, "getFilterFromID", side_effect=PersistentQueryFilter.DoesNotExist):
            with self.assertRaises(ESPError_NoLog) as cm:
                self._call_handler(ListGenModule.generateList, {"filterid": "9999"})
            self.assertEqual(str(cm.exception), "The query filter ID given is invalid or has expired.")

    def test_generateList_non_numeric_filterid_raises_ESPError(self):
        with patch.object(PersistentQueryFilter, "getFilterFromID", side_effect=AssertionError):
            with self.assertRaises(ESPError_NoLog) as cm:
                self._call_handler(ListGenModule.generateList, {"filterid": "abc"})
            self.assertEqual(str(cm.exception), "The query filter ID given is invalid or has expired.")
