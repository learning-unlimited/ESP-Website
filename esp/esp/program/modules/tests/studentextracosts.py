from esp.datatypes.models import LineItemOptions, LineItemType
from esp.program.modules.handlers.studentextracosts import StudentExtraCosts
from esp.program.modules.tests.test_framework import ProgramFrameworkTest


class StudentExtraCostsTest(ProgramFrameworkTest):
    """Unit tests for StudentExtraCosts handler and custom amount validation."""

    def setUp(self):
        super().setUp()
        self.module = StudentExtraCosts()

    def test_custom_amount_invalid_type_fails_gracefully(self):
        """Test that non-numeric custom amount input doesn't raise 500 ValueError."""
        item_type = LineItemType.objects.create(name="T-Shirt", program=self.program)
        option = LineItemOptions.objects.create(
            item_type=item_type, text="Custom Donation", is_custom=True, cost=0
        )

        post_data = {
            f"item_{item_type.id}": option.id,
            f"item_{item_type.id}_amount": "invalid_string_amount",
        }

        request = self.factory.post("/studentextracosts/", post_data)
        request.user = self.student

        response = self.module.studentextracosts(
            request, self.tl, "one", "two", "module", "extra", self.program
        )
        self.assertEqual(response.status_code, 200)
