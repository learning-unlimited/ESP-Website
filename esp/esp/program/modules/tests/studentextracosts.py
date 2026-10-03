from django.test import RequestFactory, TestCase

from esp.accounting.models import LineItemOptions, LineItemType
from esp.program.models import Program
from esp.program.modules.handlers.studentextracosts import StudentExtraCosts
from esp.users.models import ESPUser


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
