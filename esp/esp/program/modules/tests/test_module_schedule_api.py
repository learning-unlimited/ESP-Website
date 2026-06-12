import json
from datetime import datetime, timedelta

from django.urls import reverse
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj

class TestModuleScheduleAPI(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()

        self.admin = self.admins[0]
        self.student = self.students[0]

        # Grab a real module linked to the program
        mod = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list('id', flat=True)
        ).first()

        self.pmo = ProgramModuleObj.getFromProgModule(self.program, mod)

        self.now = datetime.now()
        self.past = self.now - timedelta(days=1)
        self.future = self.now + timedelta(days=1)

        # Kwargs for URL resolution
        self.url_kwargs = {
            'program_type': self.program.program_type,
            'program_term': self.program.program_instance
        }

    def test_module_schedule_api_auth(self):
        """Only admins can access the schedule API."""
        response = self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs))
        self.assertEqual(response.status_code, 403) # PermissionDenied returns 403

        self.client.force_login(self.student)
        response = self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs))
        self.assertEqual(response.status_code, 200)

    def test_module_schedule_api_get(self):
        """GET returns grouped modules."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["program_id"], self.program.id)
        self.assertIn("learn", data["modules"])

        # Find our pmo in the response
        found = False
        for mod_list in data["modules"].values():
            for m in mod_list:
                if m["id"] == self.pmo.id:
                    found = True
                    break
        self.assertTrue(found)

    def test_module_schedule_update_api(self):
        """PATCH/POST to update saves new dates and seq."""
        self.client.force_login(self.admin)

        payload = {
            "module_id": self.pmo.id,
            "start_date": self.past.isoformat(),
            "end_date": self.future.isoformat(),
            "seq": 999
        }

        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        # Verify DB updated
        self.pmo.refresh_from_db()
        self.assertEqual(self.pmo.seq, 999)
        self.assertIsNotNone(self.pmo.start_date)
        self.assertIsNotNone(self.pmo.end_date)

    def test_module_schedule_update_validation(self):
        """Cannot set start_date after end_date."""
        self.client.force_login(self.admin)

        payload = {
            "module_id": self.pmo.id,
            "start_date": self.future.isoformat(),
            "end_date": self.past.isoformat()
        }

        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])

    def test_module_schedule_required_toggle_api(self):
        """Toggle required flags and label."""
        self.client.force_login(self.admin)

        payload = {
            "module_id": self.pmo.id,
            "required": True,
            "required_label": "Must do this!"
        }

        response = self.client.post(
            reverse("module_schedule_required_toggle_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        self.pmo.refresh_from_db()
        self.assertTrue(self.pmo.required)
        self.assertEqual(self.pmo.required_label, "Must do this!")

    def test_module_schedule_preview_api(self):
        """Preview API filters based on `at` timestamp."""
        self.pmo.start_date = self.past
        self.pmo.end_date = self.future
        self.pmo.save()

        self.client.force_login(self.admin)

        # Now (active)
        url = reverse("module_schedule_preview_api", kwargs=self.url_kwargs) + f"?at={self.now.isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        found = False
        for mod_list in data["modules"].values():
            for m in mod_list:
                if m["id"] == self.pmo.id:
                    found = True
        self.assertTrue(found)

        # Way past (inactive)
        way_past = self.past - timedelta(days=5)
        url = reverse("module_schedule_preview_api", kwargs=self.url_kwargs) + f"?at={way_past.isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        found = False
        for mod_list in data["modules"].values():
            for m in mod_list:
                if m["id"] == self.pmo.id:
                    found = True
        self.assertFalse(found)
