import json
from datetime import datetime, timedelta

from django.test import Client
from django.urls import reverse
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj

# Create a mock handler class for testing seq_locked
class LockedModuleTestHandler(ProgramModuleObj):
    seq_locked = True
    always_enabled = True
    conflicts_with = ["ConflictingModuleHandler"]

class TestModuleScheduleConflictsAPI(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()

        self.admin = self.admins[0]

        # Clear any existing modules from the program to ensure test isolation
        self.program.program_modules.clear()
        
        # Grab or create two real modules linked to the program
        mod_qs = ProgramModule.objects.all()
        if mod_qs.count() >= 2:
            self.mod1 = mod_qs[0]
            self.mod2 = mod_qs[1]
        else:
            self.mod1 = ProgramModule.objects.create(admin_title="Test Mod 1", module_type="learn", handler="StudentRegTwoPhase", seq=1)
            self.mod2 = ProgramModule.objects.create(admin_title="Test Mod 2", module_type="teach", handler="TeacherClassRegModule", seq=2)
            
        self.program.program_modules.add(self.mod1)
        self.program.program_modules.add(self.mod2)
        self.program.save()

        self.pmo1 = ProgramModuleObj.getFromProgModule(self.program, self.mod1)
        self.pmo2 = ProgramModuleObj.getFromProgModule(self.program, self.mod2)

        self.now = datetime.now()
        self.past = self.now - timedelta(days=2)
        self.future = self.now + timedelta(days=2)
        self.base_url = f"/manage/{self.program.program_type}/{self.program.program_instance}/module_schedule"

    def test_seq_locked_blocks_update(self):
        """Updating a seq-locked module should return 403."""
        # Mock the handler class of pmo1 to be locked
        original_class = self.pmo1.__class__
        self.pmo1.__class__ = LockedModuleTestHandler

        # We also need to patch getFromProgModule temporarily so the view sees it as locked
        # But wait, we can just modify the class dynamically for the test!
        original_locked = original_class.seq_locked
        original_class.seq_locked = True

        try:
            self.client.force_login(self.admin)
            payload = {
                "module_id": self.pmo1.id,
                "seq": 999
            }

            response = self.client.post(
                self.base_url + "/update/",
                data=json.dumps(payload),
                content_type="application/json"
            )
            self.assertEqual(response.status_code, 403)
            data = json.loads(response.content)
            self.assertFalse(data["success"])
            self.assertIn("locked", data["error"])
        finally:
            original_class.seq_locked = original_locked

    def test_conflicts_api_no_overlap(self):
        """Conflicting handlers with no time overlap return no conflicts."""
        self.client.force_login(self.admin)

        original_class = self.pmo1.__class__
        original_conflicts = original_class.conflicts_with

        try:
            # Set pmo1 to conflict with pmo2's handler
            original_class.conflicts_with = [self.pmo2.module.handler]

            # No time overlap
            self.pmo1.start_date = self.past
            self.pmo1.end_date = self.now

            self.pmo2.start_date = self.future
            self.pmo2.end_date = self.future + timedelta(days=1)

            self.pmo1.save()
            self.pmo2.save()

            response = self.client.get(self.base_url + "/conflicts/")
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(len(data["conflicts"]), 0)
        finally:
            original_class.conflicts_with = original_conflicts

    def test_conflicts_api_with_overlap(self):
        """Conflicting handlers with overlapping times return conflicts."""
        self.client.force_login(self.admin)

        original_class = self.pmo1.__class__
        original_conflicts = original_class.conflicts_with

        try:
            # Set pmo1 to conflict with pmo2's handler
            original_class.conflicts_with = [self.pmo2.module.handler]

            # Time overlap
            self.pmo1.start_date = self.past
            self.pmo1.end_date = self.future

            self.pmo2.start_date = self.now
            self.pmo2.end_date = self.future + timedelta(days=5)

            self.pmo1.save()
            self.pmo2.save()

            response = self.client.get(self.base_url + "/conflicts/")
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertEqual(len(data["conflicts"]), 1)

            conflict = data["conflicts"][0]
            self.assertEqual(conflict["module_id_1"], self.pmo1.id)
            self.assertEqual(conflict["module_id_2"], self.pmo2.id)
            self.assertIsNotNone(conflict["overlap_start"])
            self.assertIsNotNone(conflict["overlap_end"])
        finally:
            original_class.conflicts_with = original_conflicts
