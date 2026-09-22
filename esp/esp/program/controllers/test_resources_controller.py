"""
Direct unit tests for ResourceController (esp/program/controllers/resources.py).

This controller manages program infrastructure: timeslots, resource types,
classrooms and equipment. It currently has 0% coverage.

Refs: #4842, #3780
"""

from unittest.mock import MagicMock

from django.db.models import ProtectedError

from esp.cal.models import Event
from esp.middleware import ESPError
from esp.program.controllers.resources import ResourceController
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import Resource, ResourceType


class ResourceControllerTimeslotTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.controller = ResourceController(self.program)

    def test_delete_timeslot_removes_event(self):
        slot = self.program.getTimeSlots().first()
        slot_id = slot.id
        self.controller.delete_timeslot(slot_id)
        self.assertFalse(Event.objects.filter(id=slot_id).exists())

    def test_add_or_edit_timeslot_create_delegates_to_form(self):
        form = MagicMock()
        form.cleaned_data = {"id": None}
        slot = self.controller.add_or_edit_timeslot(form)
        form.save_timeslot.assert_called_once()
        self.assertEqual(form.save_timeslot.call_args[0][0], self.program)
        # New unsaved Event passed through
        self.assertEqual(form.save_timeslot.call_args[0][1], slot)

    def test_add_or_edit_timeslot_edit_loads_existing(self):
        slot = self.program.getTimeSlots().first()
        form = MagicMock()
        form.cleaned_data = {"id": slot.id}
        result = self.controller.add_or_edit_timeslot(form)
        self.assertEqual(result.id, slot.id)
        form.save_timeslot.assert_called_once()


class ResourceControllerRestypeTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.controller = ResourceController(self.program)

    def test_delete_restype_removes_unreferenced_type(self):
        rt = ResourceType.objects.create(
            name="TestDeleteType", program=self.program, consumable=False
        )
        rt_id = rt.id
        self.controller.delete_restype(rt_id)
        self.assertFalse(ResourceType.objects.filter(id=rt_id).exists())

    def test_delete_restype_protected_raises_esp_error(self):
        rt = ResourceType.objects.create(
            name="TestProtectedType", program=self.program, consumable=False
        )
        original_delete = ResourceType.delete

        def failing_delete(self, *a, **k):
            raise ProtectedError("protected", [])

        ResourceType.delete = failing_delete
        try:
            with self.assertRaises(ESPError):
                self.controller.delete_restype(rt.id)
        finally:
            ResourceType.delete = original_delete
        # Original row still exists since delete failed
        self.assertTrue(ResourceType.objects.filter(id=rt.id).exists())

    def test_add_or_edit_restype_create(self):
        form = MagicMock()
        form.cleaned_data = {"id": None}
        result = self.controller.add_or_edit_restype(form, choices=[])
        form.save_restype.assert_called_once()
        self.assertEqual(form.save_restype.call_args[0][0], self.program)
        self.assertEqual(form.save_restype.call_args[0][1], result)

    def test_add_or_edit_restype_edit(self):
        rt = ResourceType.objects.create(
            name="TestEditType", program=self.program, consumable=False
        )
        form = MagicMock()
        form.cleaned_data = {"id": rt.id}
        result = self.controller.add_or_edit_restype(form)
        self.assertEqual(result.id, rt.id)


class ResourceControllerClassroomEquipmentTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.controller = ResourceController(self.program)

    def test_delete_classroom_unschedules_and_removes(self):
        classrooms = list(self.program.getClassrooms())
        if not classrooms:
            self.skipTest("No classrooms in fixture program")
        target = classrooms[0]
        name = target.name
        self.controller.delete_classroom(target.id)
        # All rooms sharing the name are removed
        self.assertEqual(
            self.program.getClassrooms().filter(name=name).count(), 0
        )

    def test_add_or_edit_classroom_delegates_to_form(self):
        form = MagicMock()
        self.controller.add_or_edit_classroom(form, furnishings=[])
        form.save_classroom.assert_called_once_with(
            self.program, furnishings=[]
        )

    def test_delete_equipment_removes_program_resources(self):
        resource = Resource.objects.filter(event__program=self.program).first()
        if resource is None:
            self.skipTest("No program resources in fixture program")
        # identical_resources + program filter may match several rows;
        # at minimum the targeted id must be gone afterwards.
        target_id = resource.id
        self.controller.delete_equipment(target_id)
        self.assertFalse(Resource.objects.filter(id=target_id).exists())
