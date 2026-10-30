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

    def test_module_schedule_update_syncs_permissions(self):
        """Updating module schedule dates automatically syncs Permission records."""
        self.client.force_login(self.admin)
        from esp.program.models import ProgramModule
        from esp.program.modules.base import ProgramModuleObj
        from esp.users.models import Permission
        from django.contrib.auth.models import Group

        mod = ProgramModule.objects.filter(handler="StudentClassRegModule").first()
        if not mod:
            mod = ProgramModule.objects.create(
                admin_title="Student Class Registration",
                module_type="learn",
                handler="StudentClassRegModule",
                seq=10
            )
        self.program.program_modules.add(mod)
        pmo = ProgramModuleObj.getFromProgModule(self.program, mod)

        student_group = Group.objects.get(name="Student")
        # Ensure no existing permission record for Student/Classes on this program
        Permission.objects.filter(
            program=self.program,
            role=student_group,
            permission_type="Student/Classes"
        ).delete()

        payload = {
            "module_id": pmo.id,
            "start_date": self.past.isoformat(),
            "end_date": self.future.isoformat(),
            "seq": 10
        }

        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        # Check DB for created Permission record
        perm = Permission.objects.filter(
            program=self.program,
            role=student_group,
            permission_type="Student/Classes",
            user__isnull=True,
            user_filter__isnull=True
        ).first()
        self.assertIsNotNone(perm)
        self.assertEqual(perm.start_date, self.past)
        self.assertEqual(perm.end_date, self.future)

        # Test updating the dates again
        new_past = self.past - timedelta(days=2)
        new_future = self.future + timedelta(days=2)
        payload = {
            "module_id": pmo.id,
            "start_date": new_past.isoformat(),
            "end_date": new_future.isoformat(),
            "seq": 10
        }
        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        perm.refresh_from_db()
        self.assertEqual(perm.start_date, new_past)
        self.assertEqual(perm.end_date, new_future)

        # Also test TeacherClassRegModule
        teacher_mod = ProgramModule.objects.filter(handler="TeacherClassRegModule").first()
        if not teacher_mod:
            teacher_mod = ProgramModule.objects.create(
                admin_title="Teacher Class Registration",
                module_type="teach",
                handler="TeacherClassRegModule",
                seq=10
            )
        self.program.program_modules.add(teacher_mod)
        tpmo = ProgramModuleObj.getFromProgModule(self.program, teacher_mod)
        teacher_group = Group.objects.get(name="Teacher")

        payload = {
            "module_id": tpmo.id,
            "start_date": self.past.isoformat(),
            "end_date": self.future.isoformat(),
            "seq": 10
        }
        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        tperm = Permission.objects.filter(
            program=self.program,
            role=teacher_group,
            permission_type="Teacher/Classes/All",
            user__isnull=True,
            user_filter__isnull=True
        ).first()
        self.assertIsNotNone(tperm)
        self.assertEqual(tperm.start_date, self.past)
        self.assertEqual(tperm.end_date, self.future)

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
        self.pmo.module.handler = 'StudentRegProfileModule'
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

    def test_export_schedule_api(self):
        """GET to export endpoint returns relative schedule template."""
        self.client.force_login(self.admin)

        base_start = datetime(2026, 9, 1, 10, 0, 0)
        base_end = base_start + timedelta(days=14)
        self.pmo.start_date = base_start
        self.pmo.end_date = base_end
        self.pmo.save()

        url = reverse("module_schedule_export_api", kwargs=self.url_kwargs) + f"?anchor={base_start.isoformat()}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertIn("schedule", data)
        self.assertNotIn("anchor_date", data)
        self.assertIn("anchor_date", data["schedule"])
        modules = data["schedule"]["modules"]
        self.assertTrue(len(modules) > 0)

        target_item = None
        for item in modules:
            if item["handler"] == self.pmo.module.handler:
                target_item = item
                break

        self.assertIsNotNone(target_item)
        self.assertEqual(target_item["start_offset_seconds"], 0)
        self.assertEqual(target_item["end_offset_seconds"], 14 * 86400)

    def test_import_schedule_api(self):
        """POST to import endpoint applies relative schedule to target program."""
        from esp.program.models import Program
        self.client.force_login(self.admin)

        target_prog = Program.objects.create(
            url="TargetDev/2027",
            name="Target Dev 2027",
            grade_min=7,
            grade_max=12
        )
        target_prog.program_modules.add(self.pmo.module)

        target_kwargs = {
            'program_type': 'TargetDev',
            'program_term': '2027'
        }

        template_payload = {
            "target_start_date": "2027-04-01T09:00:00",
            "schedule": {
                "version": "1.0",
                "modules": [
                    {
                        "handler": self.pmo.module.handler,
                        "seq": 15,
                        "required": True,
                        "link_title": "Imported Title",
                        "start_offset_seconds": 0,
                        "end_offset_seconds": 7 * 86400
                    }
                ]
            }
        }

        url = reverse("module_schedule_import_api", kwargs=target_kwargs)
        response = self.client.post(url, json.dumps(template_payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["updated_count"], 1)

        from esp.program.modules.base import ProgramModuleObj
        target_pmo = ProgramModuleObj.getFromProgModule(target_prog, self.pmo.module)
        self.assertEqual(target_pmo.start_date, datetime(2027, 4, 1, 9, 0, 0))
        self.assertEqual(target_pmo.end_date, datetime(2027, 4, 8, 9, 0, 0))
        self.assertEqual(target_pmo.link_title, "Imported Title")

    def test_import_schedule_api_rollback_on_invalid_date(self):
        """If one module has invalid dates (start >= end), transaction rolls back completely."""
        from esp.program.models import Program
        self.client.force_login(self.admin)

        target_prog = Program.objects.create(
            url="RollbackDev/2027",
            name="Rollback Dev 2027",
            grade_min=7,
            grade_max=12
        )
        target_prog.program_modules.add(self.pmo.module)
        target_pmo = ProgramModuleObj.getFromProgModule(target_prog, self.pmo.module)
        original_start = target_pmo.start_date

        target_kwargs = {
            'program_type': 'RollbackDev',
            'program_term': '2027'
        }

        second_mod = ProgramModule.objects.exclude(id=self.pmo.module.id).first()
        second_handler = second_mod.handler if second_mod else "StudentRegConfirm"

        template_payload = {
            "target_start_date": "2027-04-01T09:00:00",
            "schedule": {
                "version": "1.0",
                "modules": [
                    {
                        "handler": self.pmo.module.handler,
                        "seq": 15,
                        "required": True,
                        "link_title": "Should Rollback",
                        "start_offset_seconds": 0,
                        "end_offset_seconds": 7 * 86400
                    },
                    {
                        "handler": second_handler,
                        "seq": 20,
                        "required": True,
                        "start_offset_seconds": 100,
                        "end_offset_seconds": 50  # Invalid: start > end
                    }
                ]
            }
        }

        url = reverse("module_schedule_import_api", kwargs=target_kwargs)
        response = self.client.post(url, json.dumps(template_payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Calculated start_date is after end_date", data["error"])

        # Verify DB was rolled back for the first module
        target_pmo.refresh_from_db()
        self.assertEqual(target_pmo.start_date, original_start)
        self.assertNotEqual(target_pmo.link_title, "Should Rollback")

    def test_import_schedule_api_strict_boolean(self):
        """Passing non-boolean values for 'required' returns 400 Bad Request."""
        self.client.force_login(self.admin)
        template_payload = {
            "target_start_date": "2027-04-01T09:00:00",
            "schedule": {
                "version": "1.0",
                "modules": [
                    {
                        "handler": self.pmo.module.handler,
                        "seq": 15,
                        "required": "false",  # String instead of bool
                        "start_offset_seconds": 0,
                        "end_offset_seconds": 86400
                    }
                ]
            }
        }
        url = reverse("module_schedule_import_api", kwargs=self.url_kwargs)
        response = self.client.post(url, json.dumps(template_payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("must be a boolean", data["error"])

    def test_import_schedule_api_rejects_overlong_strings(self):
        """Import rejects an overlong link_title before saving to the database."""
        self.client.force_login(self.admin)
        template_payload = {
            "target_start_date": "2027-04-01T09:00:00",
            "schedule": {
                "version": "1.0",
                "modules": [
                    {
                        "handler": self.pmo.module.handler,
                        "seq": 15,
                        "required": True,
                        "link_title": "x" * 65,
                        "start_offset_seconds": 0,
                        "end_offset_seconds": 86400
                    }
                ]
            }
        }
        url = reverse("module_schedule_import_api", kwargs=self.url_kwargs)
        response = self.client.post(url, json.dumps(template_payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("link_title must be 64 characters or fewer", data["error"])

    def test_import_schedule_api_rejects_overlong_required_label(self):
        """Import rejects an overlong required_label before saving to the database."""
        self.client.force_login(self.admin)
        template_payload = {
            "target_start_date": "2027-04-01T09:00:00",
            "schedule": {
                "version": "1.0",
                "modules": [
                    {
                        "handler": self.pmo.module.handler,
                        "seq": 15,
                        "required": True,
                        "required_label": "y" * 81,
                        "start_offset_seconds": 0,
                        "end_offset_seconds": 86400
                    }
                ]
            }
        }
        url = reverse("module_schedule_import_api", kwargs=self.url_kwargs)
        response = self.client.post(url, json.dumps(template_payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("required_label must be 80 characters or fewer", data["error"])

    def test_export_and_import_schedule_api_non_admin_forbidden(self):
        """Non-admin users receive 403 Forbidden for export and import endpoints."""
        export_url = reverse("module_schedule_export_api", kwargs=self.url_kwargs)
        import_url = reverse("module_schedule_import_api", kwargs=self.url_kwargs)

        # Unauthenticated
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(import_url, "{}", content_type="application/json")
        self.assertEqual(response.status_code, 403)

        # Student user
        self.client.force_login(self.student)
        response = self.client.get(export_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(import_url, "{}", content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def _post_import(self, modules, url_kwargs=None, target_start_date="2027-04-01T09:00:00"):
        url = reverse("module_schedule_import_api", kwargs=url_kwargs or self.url_kwargs)
        payload = {"target_start_date": target_start_date, "schedule": {"version": "1.0", "modules": modules}}
        return self.client.post(url, json.dumps(payload), content_type="application/json")

    def test_export_import_round_trip(self):
        """Exporting one program and importing into another preserves relative offsets."""
        from esp.program.models import Program
        self.client.force_login(self.admin)

        self.pmo.start_date = datetime(2026, 9, 1, 10, 0, 0)
        self.pmo.end_date = datetime(2026, 9, 15, 10, 0, 0)
        self.pmo.save()

        response = self.client.get(reverse("module_schedule_export_api", kwargs=self.url_kwargs))
        schedule = json.loads(response.content)["schedule"]

        target_prog = Program.objects.create(url="RoundTrip/2027", name="Round Trip 2027", grade_min=7, grade_max=12)
        url = reverse("module_schedule_import_api", kwargs={'program_type': 'RoundTrip', 'program_term': '2027'})
        payload = {"target_start_date": "2027-09-01T10:00:00", "schedule": schedule}
        response = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)

        target_pmo = ProgramModuleObj.getFromProgModule(target_prog, self.pmo.module)
        self.assertTrue(target_prog.program_modules.filter(id=self.pmo.module.id).exists())
        self.assertEqual(target_pmo.end_date - target_pmo.start_date, timedelta(days=14))

    def test_import_matches_handler_and_module_type(self):
        """Handlers shared by several modules (e.g. AdmissionsDashboard) are matched by module_type too."""
        teach_mod = ProgramModule.objects.filter(handler="AdmissionsDashboard", module_type="teach").first()
        manage_mod = ProgramModule.objects.filter(handler="AdmissionsDashboard", module_type="manage").first()
        if not (teach_mod and manage_mod):
            self.skipTest("AdmissionsDashboard modules are not installed")
        self.program.program_modules.add(teach_mod, manage_mod)
        self.client.force_login(self.admin)

        response = self._post_import([
            {"handler": "AdmissionsDashboard", "module_type": "teach", "start_offset_seconds": 0, "end_offset_seconds": 86400},
            {"handler": "AdmissionsDashboard", "module_type": "manage", "start_offset_seconds": 0, "end_offset_seconds": 2 * 86400},
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["updated_count"], 2)

        teach_pmo = ProgramModuleObj.objects.get(program=self.program, module=teach_mod)
        manage_pmo = ProgramModuleObj.objects.get(program=self.program, module=manage_mod)
        self.assertEqual(teach_pmo.end_date, datetime(2027, 4, 2, 9, 0, 0))
        self.assertEqual(manage_pmo.end_date, datetime(2027, 4, 3, 9, 0, 0))

    def test_import_rejects_malformed_items(self):
        """Malformed module entries return 400 with a safe message instead of a 500 or a raw exception."""
        self.client.force_login(self.admin)
        handler = self.pmo.module.handler
        bad_payloads = [
            ["not-a-dict"],
            [{"handler": handler, "start_offset_seconds": "abc"}],
            [{"handler": handler, "start_offset_seconds": 10 ** 18}],
            [{"handler": handler, "seq": "abc"}],
        ]
        for modules in bad_payloads:
            with self.subTest(modules=modules):
                response = self._post_import(modules)
                self.assertEqual(response.status_code, 400)
                error = json.loads(response.content)["error"]
                self.assertNotIn("invalid literal", error)

    def test_import_unknown_handlers_only(self):
        """A template whose handlers are all unknown is rejected."""
        self.client.force_login(self.admin)
        response = self._post_import([{"handler": "NoSuchModule", "start_offset_seconds": 0}])
        self.assertEqual(response.status_code, 400)
