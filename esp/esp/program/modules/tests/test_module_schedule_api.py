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

    def test_reorder_success(self):
        """POST a valid reorder should update seq values in the DB."""
        self.client.force_login(self.admin)

        # Get another PMO from the program (there should be at least one)
        another_mod = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list('id', flat=True)
        ).exclude(id=self.pmo.module.id).first()

        if another_mod is None:
            self.skipTest("Need at least two modules to test reorder.")

        pmo2 = ProgramModuleObj.getFromProgModule(self.program, another_mod)

        url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)
        payload = {
            "order": [
                {"id": self.pmo.id, "seq": 50},
                {"id": pmo2.id, "seq": 10}
            ]
        }
        response = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        self.pmo.refresh_from_db()
        pmo2.refresh_from_db()
        self.assertEqual(self.pmo.seq, 50)
        self.assertEqual(pmo2.seq, 10)

    def test_reorder_rejects_locked_module(self):
        """Attempting to reorder a position_locked module should return 403 and not save anything."""
        self.client.force_login(self.admin)

        original_seq = self.pmo.seq
        original_handler = self.pmo.module.handler
        
        # Temporarily make this module locked in the DB
        self.pmo.module.handler = 'RegProfileModule'
        self.pmo.module.save()

        try:
            url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)
            payload = {
                "order": [
                    {"id": self.pmo.id, "seq": 999}
                ]
            }
            response = self.client.post(url, json.dumps(payload), content_type="application/json")
            self.assertEqual(response.status_code, 403)
            data = json.loads(response.content)
            self.assertFalse(data["success"])
            self.assertIn("locked", data["error"])
        finally:
            self.pmo.module.handler = original_handler
            self.pmo.module.save()

        # Verify the seq was not changed (transaction was rolled back)
        self.pmo.refresh_from_db()
        self.assertEqual(self.pmo.seq, original_seq)

    def test_reorder_rejects_wrong_program(self):
        """Module IDs from a different program should be silently ignored."""
        from esp.program.models import Program
        self.client.force_login(self.admin)

        # Create a minimal second program and a PMO for it
        prog2 = Program.objects.create(
            url="OtherDev/2026",
            name="Other Dev 2026",
            grade_min=7,
            grade_max=12,
        )
        extra_mod = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list('id', flat=True)
        ).first()
        prog2.program_modules.add(extra_mod)
        pmo_other = ProgramModuleObj.getFromProgModule(prog2, extra_mod)
        original_seq = pmo_other.seq

        url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)
        payload = {
            "order": [
                {"id": pmo_other.id, "seq": 10}
            ]
        }
        response = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        pmo_other.refresh_from_db()
        # The seq should be unchanged because pmo_other belongs to prog2, not self.program
        self.assertEqual(pmo_other.seq, original_seq)

    def test_reorder_requires_post(self):
        """GET to the reorder endpoint should return 405 Method Not Allowed."""
        self.client.force_login(self.admin)
        url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

