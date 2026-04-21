from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from esp.program.modules.handlers.programprintables import ProgramPrintables


class _FakeTransfers(list):
    def __init__(self, values):
        super().__init__(values)
        self.exclude_kwargs = None
        self.filter_kwargs = None

    def exclude(self, **kwargs):
        self.exclude_kwargs = kwargs
        return self

    def filter(self, **kwargs):
        self.filter_kwargs = kwargs
        return self

    def order_by(self, *args):
        return self

    def select_related(self):
        return self


class PaidListInvalidFilterTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.module = SimpleNamespace(baseDir=lambda: "")

    def test_non_integer_filter_falls_back_without_crashing(self):
        request = self.factory.get("/manage/program/paid_list", {"filter": "abc"})
        prog = SimpleNamespace()
        lineitem = SimpleNamespace(user=SimpleNamespace(last_name="Tester", hasFinancialAid=lambda p: False))
        fake_transfers = _FakeTransfers([lineitem])

        paid_list_fn = getattr(ProgramPrintables.paid_list, "method", ProgramPrintables.paid_list)

        with patch(
            "esp.program.modules.handlers.programprintables.ProgramAccountingController"
        ) as pac_cls, patch(
            "esp.program.modules.handlers.programprintables.render_to_response",
            return_value=HttpResponse("ok"),
        ) as render_mock:
            pac_cls.return_value.all_transfers.return_value = fake_transfers

            response = paid_list_fn(self.module, request, None, None, None, None, None, prog)

        self.assertEqual(response.status_code, 200)
        render_args, render_kwargs = render_mock.call_args
        context = render_args[2] if len(render_args) > 2 else render_kwargs["context"]
        self.assertEqual(context["single_select"], False)
        self.assertEqual(len(context["lineitems"]), 1)
        self.assertIsNone(fake_transfers.filter_kwargs)
        self.assertEqual(fake_transfers.exclude_kwargs, {"line_item__text__in": ["Sibling discount", "Program admission", "Financial aid grant", "Student payment"]})

    def test_mixed_valid_and_invalid_filter_keeps_valid_id_subset(self):
        request = self.factory.get("/manage/program/paid_list", {"filter": ["12", "abc"]})
        prog = SimpleNamespace()
        lineitem = SimpleNamespace(user=SimpleNamespace(last_name="Tester", hasFinancialAid=lambda p: False))
        fake_transfers = _FakeTransfers([lineitem])

        paid_list_fn = getattr(ProgramPrintables.paid_list, "method", ProgramPrintables.paid_list)

        with patch(
            "esp.program.modules.handlers.programprintables.ProgramAccountingController"
        ) as pac_cls, patch(
            "esp.program.modules.handlers.programprintables.render_to_response",
            return_value=HttpResponse("ok"),
        ) as render_mock:
            pac_cls.return_value.all_transfers.return_value = fake_transfers

            response = paid_list_fn(self.module, request, None, None, None, None, None, prog)

        self.assertEqual(response.status_code, 200)
        render_args, render_kwargs = render_mock.call_args
        context = render_args[2] if len(render_args) > 2 else render_kwargs["dictionary"]
        self.assertEqual(context["single_select"], True)
        self.assertEqual(len(context["lineitems"]), 1)
        self.assertEqual(fake_transfers.filter_kwargs, {"line_item__id__in": [12]})
        self.assertIsNone(fake_transfers.exclude_kwargs)
