from decimal import Decimal

from django.test import RequestFactory, TestCase

from esp.accounting.models import LineItemOptions, LineItemType, Transfer
from esp.program.models import Program
from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.handlers.studentextracosts import StudentExtraCosts
from esp.users.models import ESPUser, RecordType


class StudentExtraCostsTest(TestCase):
    """Unit tests for StudentExtraCosts handler and custom amount validation."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = ESPUser.objects.create_user(
            username="teststudent",
            email="teststudent@example.com",
            first_name="Test",
            last_name="Student",
        )
        self.program = Program.objects.create(
            name="Test Program",
            url="testprog",
            grade_min=6,
            grade_max=12,
        )
        self.module = StudentExtraCosts()
        self.module.program = self.program
        self.module.user = self.user

    def test_custom_amount_invalid_type_fails_gracefully(self):
        """Test that non-numeric custom amount input does not raise 500 ValueError."""
        item_type = LineItemType.objects.create(
            text="T-Shirt",
            amount_dec=10,
            program=self.program,
        )
        option = LineItemOptions.objects.create(
            lineitem_type=item_type,
            description="Custom Donation",
            is_custom=True,
            amount_dec=0,
        )

        post_data = {
            f"multi{item_type.id}_option_0": str(option.id),
            f"multi{item_type.id}_option_1": "invalid_string_amount",
        }
        request = self.factory.post(f"/learn/{self.program.url}/studentextracosts/", post_data)
        request.user = self.user
        request.session = {}

        response = self.module.extracosts(request, [self.program.url])
        self.assertEqual(response.status_code, 200)


class CustomAmountValidationTest(ProgramFrameworkTest):
    """End-to-end tests of custom amount validation for single-select line items."""

    def setUp(self):
        super().setUp(num_students=1)
        self.add_user_profiles()
        # Other tests may have flushed the built-in record types; the view needs this one on success.
        RecordType.objects.get_or_create(name="extra_costs_done", defaults={"description": "Completed the extra costs form"})
        self.student = self.students[0]
        self.item_type = LineItemType.objects.create(text="Lunch", amount_dec=10, program=self.program)
        self.option = LineItemOptions.objects.create(
            lineitem_type=self.item_type, description="Custom Amount", is_custom=True, amount_dec=0)
        self.assertTrue(self.client.login(username=self.student.username, password="password"))

    def _post_amount(self, amount):
        return self.client.post(
            "/learn/%s/extracosts" % self.program.getUrlBase(),
            {
                "multi%s-option_0" % self.item_type.id: str(self.option.id),
                "multi%s-option_1" % self.item_type.id: amount,
            },
        )

    def _transfers(self):
        return Transfer.objects.filter(user=self.student, line_item=self.item_type)

    def test_invalid_amounts_are_rejected(self):
        """Negative, non-finite, oversized, over-precise and empty amounts re-render the form and save nothing."""
        for amount in ["-50", "nan", "inf", "-inf", "1e12", "12345678.90", "12.345", "abc", ""]:
            with self.subTest(amount=amount):
                response = self._post_amount(amount)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["errors"])
                self.assertTrue(response.context["error_custom"])
                self.assertFalse(self._transfers().exists())

    def test_valid_amounts_are_saved_exactly(self):
        """Valid amounts are saved as the exact Decimal and the student is redirected onward."""
        for amount, expected in [("25.00", Decimal("25.00")), ("0", Decimal("0")),
                                 ("7.5", Decimal("7.50")), ("9999999.99", Decimal("9999999.99"))]:
            with self.subTest(amount=amount):
                response = self._post_amount(amount)
                self.assertEqual(response.status_code, 302)
                self.assertEqual([t.amount_dec for t in self._transfers()], [expected])

    def test_multi_select_accepts_zero_custom_amount(self):
        """A zero custom amount is valid for multi-select items, as for single-select."""
        item_type = LineItemType.objects.create(
            text="Snacks", amount_dec=10, program=self.program, selection_type="multiple")
        option = LineItemOptions.objects.create(
            lineitem_type=item_type, description="Custom Snack", is_custom=True, amount_dec=0)
        response = self.client.post(
            "/learn/%s/extracosts" % self.program.getUrlBase(),
            {
                "multi%s-options" % item_type.id: [str(option.id)],
                "multi%s-custom_amount_%s" % (item_type.id, option.id): "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        transfers = Transfer.objects.filter(user=self.student, line_item=item_type)
        self.assertEqual([t.amount_dec for t in transfers], [Decimal("0")])
