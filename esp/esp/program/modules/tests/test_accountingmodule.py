from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from esp.accounting.views import user_accounting


class AccountingModuleTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="test_admin",
            password="password123"
        )

    def test_user_lookup_via_url_extra(self):
        """
        Verify lookup via URL query parameter
        """
        request = self.factory.get(f"/accounting/?extra={self.user.id}")
        request.user = self.user

        response = user_accounting(request)

        # just verify response exists
        self.assertIsNotNone(response)

    def test_user_lookup_via_post_data(self):
        """
        Verify lookup via POST data
        """
        request = self.factory.post(
            "/accounting/",
            {"target_user": self.user.id}
        )
        request.user = self.user

        response = user_accounting(request)

        self.assertIsNotNone(response)

    def test_invalid_user_lookup(self):
        """
        Invalid user should not crash the view
        """
        request = self.factory.get("/accounting/?extra=99999")
        request.user = self.user

        response = user_accounting(request)

        self.assertIsNotNone(response)