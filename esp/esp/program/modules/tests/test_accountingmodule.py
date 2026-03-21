from django.test import TestCase, RequestFactory
from esp.accounting.views import user_summary
from esp.users.models import ESPUser


class AccountingModuleTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = ESPUser.objects.create_user(
            username="test_admin",
            password="password123"
        )
        self.user.makeAdmin()

    def test_user_lookup_via_url_target_user(self):
        
        
        request = self.factory.get(
            f"/accounting/?target_user={self.user.id}"
        )
        request.user = self.user

        response = user_summary(request)

        self.assertEqual(response.status_code, 200)

    def test_user_lookup_via_post_data(self):
        """
        Verify lookup via POST data
        """
        request = self.factory.post(
            "/accounting/",
            {"target_user": self.user.id}
        )
        request.user = self.user

        response = user_summary(request)

        self.assertEqual(response.status_code, 200)

    def test_invalid_user_lookup(self):
        """
        Invalid user should not crash the view
        """
        request = self.factory.get("/accounting/?target_user=99999")
        request.user = self.user

        response = user_summary(request)

        self.assertEqual(response.status_code, 200)